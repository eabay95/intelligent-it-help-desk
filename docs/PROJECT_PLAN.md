# Project plan (proposal)

## User flow
1. Employee opens the support portal.
2. Employee enters an issue title and description and submits a ticket.
3. Backend records the ticket and sends its text to the R classifier.
4. Classifier predicts an issue category; the application derives a recommended support team and estimated priority.
5. Technician reviews the queue, adjusts predictions if needed, and works on the ticket.
6. Technician marks the ticket resolved; employee sees the updated status.

## Initial categories (to confirm)
- Network
- Account / Access
- Hardware
- Software
- Other

## Planned ticket fields (to confirm)
Ticket ID, requester, title, description, category, suggested team, priority, status, created date, last updated date.

## Suggested milestones
1. Agree on requirements, categories, and ticket fields.
2. Define request/response data contracts.
3. Build basic frontend and backend independently.
4. Prepare labeled dataset and train/evaluate R text classifier.
5. Connect prediction service and ticket flow.
6. Deploy on AWS and evaluate end-to-end demo.

## Scope
The initial version supports internal employee IT support. Customer-facing support can be added as a future expansion; it is not included in this skeleton.
