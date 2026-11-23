"""Add Supabase profiles and authenticated ticket ownership."""

import sqlalchemy as sa
from alembic import op

revision = "0001_supabase_identity"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    existing_policies = op.get_bind().execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tickets'
        )
    """)).scalar_one()
    if existing_policies:
        raise RuntimeError("Review the existing ticket RLS policies before adopting this table.")

    op.execute("ALTER TABLE public.helpdesk_alembic_version ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON public.helpdesk_alembic_version FROM PUBLIC, anon, authenticated")

    # The MVP initialized this table at startup. Adopt it if it already exists.
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.tickets (
            id SERIAL PRIMARY KEY,
            title VARCHAR(160) NOT NULL,
            description TEXT NOT NULL,
            requester_id VARCHAR(64) NOT NULL,
            category VARCHAR(40) NOT NULL,
            priority VARCHAR(12) NOT NULL,
            recommended_team VARCHAR(120) NOT NULL,
            status VARCHAR(20) NOT NULL,
            classification_source VARCHAR(12) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE public.profiles (
            id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
            full_name TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL DEFAULT 'employee' CHECK (role IN ('employee', 'technician')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE FUNCTION public.helpdesk_create_profile() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
        BEGIN
            INSERT INTO public.profiles (id, full_name)
            VALUES (NEW.id, LEFT(TRIM(COALESCE(NEW.raw_user_meta_data->>'full_name', '')), 120))
            ON CONFLICT (id) DO NOTHING;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("REVOKE EXECUTE ON FUNCTION public.helpdesk_create_profile() FROM PUBLIC, anon, authenticated")
    op.execute("""
        CREATE TRIGGER helpdesk_create_profile AFTER INSERT ON auth.users
        FOR EACH ROW EXECUTE FUNCTION public.helpdesk_create_profile()
    """)
    op.execute("""
        INSERT INTO public.profiles (id, full_name)
        SELECT id, LEFT(TRIM(COALESCE(raw_user_meta_data->>'full_name', '')), 120) FROM auth.users
        ON CONFLICT (id) DO NOTHING
    """)

    op.alter_column("tickets", "requester_id", new_column_name="legacy_requester_id",
                    nullable=True, schema="public")
    op.execute("ALTER INDEX IF EXISTS public.ix_tickets_requester_id RENAME TO ix_tickets_legacy_requester_id")
    op.add_column("tickets", sa.Column("requester_id", sa.Uuid()), schema="public")
    op.add_column("tickets", sa.Column("classification_confidence", sa.Float()), schema="public")
    op.add_column("tickets", sa.Column("classification_model_version", sa.Text()), schema="public")
    op.create_foreign_key(
        "fk_tickets_requester", "tickets", "profiles", ["requester_id"], ["id"],
        source_schema="public", referent_schema="public", ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_tickets_owner_or_legacy", "tickets",
        "requester_id IS NOT NULL OR legacy_requester_id IS NOT NULL", schema="public",
    )
    op.create_index("ix_tickets_requester_id", "tickets", ["requester_id"], schema="public")

    for table in ("profiles", "tickets"):
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON public.{table} FROM PUBLIC, anon, authenticated")
        op.execute(f"GRANT SELECT ON public.{table} TO authenticated")
    op.execute("""
        CREATE POLICY helpdesk_own_profile ON public.profiles
        FOR SELECT TO authenticated USING (id = (SELECT auth.uid()))
    """)
    op.execute("""
        CREATE POLICY helpdesk_ticket_access ON public.tickets
        FOR SELECT TO authenticated USING (
            requester_id = (SELECT auth.uid()) OR EXISTS (
                SELECT 1 FROM public.profiles WHERE id = (SELECT auth.uid()) AND role = 'technician'
            )
        )
    """)


def downgrade():
    raise RuntimeError("Restore a reviewed backup for rollback; original requester text is retained.")
