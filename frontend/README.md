# Intelligent IT Help Desk — Frontend

## Overview

The frontend for the Intelligent IT Help Desk provides a web interface for employees, customers, and IT technicians to interact with the help desk system.

Users can submit and track support tickets, while IT technicians can manage and resolve incoming requests.

## Tech Stack

- React
- JavaScript
- Vite
- React Router
- CSS

## Project Structure

```text
frontend/
├── public/
├── src/
│   ├── components/
│   │   └── Navbar.jsx
│   ├── pages/
│   │   ├── EmployeePortal.jsx
│   │   └── TechnicianDashboard.jsx
│   ├── services/
│   │   └── api.js
│   ├── styles/
│   │   └── index.css
│   ├── App.jsx
│   └── main.jsx
├── .env.example
├── index.html
├── package.json
└── README.md
```

## Setup Instructions

### 1. Navigate to the Frontend Directory

```bash
cd frontend
```

### 2. Install Dependencies

```bash
npm install
npm install react-router-dom
```

### 3. Configure Environment Variables

Create a `.env` file inside the `frontend` directory.

Add the following:

```env
VITE_API_BASE_URL=http://localhost:8000
```

This configures the frontend to communicate with the backend API.

Do not commit the `.env` file to GitHub.

### 4. Start the Development Server

```bash
npm run dev
```

Open the local URL displayed in your terminal, typically:

http://localhost:5173

## Planned Features

### Employee and Customer Portal
- Submit IT support tickets
- View existing tickets
- Track ticket status
- Receive AI-generated troubleshooting suggestions

### Technician Dashboard
- View incoming support tickets
- Manage assigned tickets
- Update ticket statuses
- Review AI-generated ticket classifications and recommendations

## Development Notes

- Reusable UI components belong in `src/components/`.
- Application pages belong in `src/pages/`.
- Backend API requests belong in `src/services/api.js`.
- Global styling belongs in `src/styles/index.css`.
- Application routing is managed through `App.jsx`.

## Status

Frontend structure and initial setup are part of Issue #1. Additional pages, functionality, and backend integration will be developed in future issues.