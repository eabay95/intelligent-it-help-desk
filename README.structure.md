# Intelligent IT Help Desk

A team project to build an IT support ticket application with AWS and R.

## Planned features (not yet implemented)
- Employees submit IT support tickets.
- R-based text classification predicts ticket categories.
- The system estimates ticket priority and recommends an IT support team.
- IT technicians view, assign, and resolve tickets.
- Suggested troubleshooting steps and detection of recurring incidents are stretch goals.

## Planned architecture
Employee web dashboard -> Backend API -> R classification service -> Ticket queue / support team

AWS EC2 will host services; AWS S3 will hold relevant project data and artifacts. Final hosting and database design will be chosen by the team.

## Team split
- Member 1: Frontend (`frontend/`): employee ticket form and IT dashboard.
- Member 2: Backend + AWS (`backend/`, `infra/`): API, ticket lifecycle, storage, and deployment.
- Member 3: ML with R (`ml-r/`): ticket dataset, classification, prioritization evaluation.
- Everyone: `docs/`, testing, integration, demo, and presentation.

See `docs/PROJECT_PLAN.md` for planned interfaces and milestones.

**Status:** Folder structure only. There is no application code or runnable service yet.
