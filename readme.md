# IIT Prediction ML Service - Healthcare Dashboard

A production-ready machine learning service with modern React frontend for predicting Interruption in Treatment (IIT) risk in HIV/ART patients.

## 🚀 Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd my_app

# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Start development server
npm run dev
```

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Key Features](#key-features)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Component Library](#component-library)
- [Error Tracking](#error-tracking)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [Available Scripts](#available-scripts)
- [Deployment](#deployment)
- [Contributing](#contributing)

## Project Overview

This project consists of two main components:
1. **Backend ML Service** (`backend/ml-service/`) - FastAPI-based prediction service with LightGBM model
2. **Frontend Dashboard** (`src/`) - Modern React web application for healthcare professionals

## Project Status

- **Project Type**: Full-Stack ML Healthcare Application
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI + LightGBM + Redis + PostgreSQL
- **Entry Point**: `src/main.tsx` (React application entry)
- **Build System**: Vite 7.0.0 (Fast development and build)
- **Styling System**: Tailwind CSS 3.4.17 with shadcn/ui components
- **Error Tracking**: Sentry integration for production monitoring

## Key Features

### Frontend Dashboard
- **Modern Healthcare UI**: Soft blue-cyan gradient palette, asymmetric layouts, generous white space
- **Real-time Predictions**: Interactive form for patient IIT risk assessment
- **Data Visualization**: Animated charts showing risk distribution and model metrics
- **Responsive Design**: Mobile-first approach optimized for healthcare workers
- **Smooth Animations**: Framer Motion powered page transitions and micro-interactions

### Backend ML Service
- **FastAPI REST API**: Async endpoints for single and batch predictions
- **LightGBM Model**: 85% AUC score with 42+ patient features
- **Redis Feature Store**: Intelligent caching with 24h TTL
- **Prometheus Metrics**: Real-time monitoring and alerting
- **Docker Deployment**: Production-ready containerized infrastructure

## Design System

### Healthcare-Optimized Color Palette
- **Primary Colors**: Soft blues (blue-500 to cyan-500) for trust and professionalism
- **Accent Colors**: Muted teal and turquoise for calm healthcare environment
- **Status Colors**: 
  - Green (low risk) - Calming and positive
  - Amber (medium risk) - Cautionary but not alarming
  - Orange (high risk) - Warning without panic
  - Red (critical risk) - Urgent attention needed
- **Neutral Tones**: Warm grays (slate-50 to slate-800) for backgrounds and text

### Typography & Spacing
- **Font Family**: Inter - Clean, modern, highly readable for medical data
- **Font Sizes**: Dramatic contrasts (3xl headers, sm body text)
- **White Space**: Generous padding and margins for reduced cognitive load
- **Line Height**: 1.5-1.75 for optimal readability of clinical information

### Animation Strategy
- **Page Transitions**: 300ms smooth fade and slide animations
- **Stat Counters**: Number counting animations for engagement
- **Progress Bars**: Animated width transitions with easing
- **Hover Effects**: Subtle scale (1.05) and shadow increases
- **Stagger Delays**: 100ms intervals for sequential reveals

### Technical Excellence
- Reusable, typed React components with clear interfaces
- Leverage React 18's concurrent features to enhance user experience
- Adopt TypeScript for type-safe development experience
- Use Zustand for lightweight state management
- Implement smooth single-page application routing through React Router DOM

## Project Architecture

### Directory Structure

```
project-root/
├── index.html              # Main HTML template
├── package.json            # Node.js dependencies and scripts
├── package-lock.json       # Lock file for npm dependencies
├── README.md              # Project documentation
├── YOUWARE.md             # Development guide and template documentation
├── yw_manifest.json       # Project manifest file
├── vite.config.ts         # Vite build tool configuration
├── tsconfig.json          # TypeScript configuration (main)
├── tsconfig.app.json      # TypeScript configuration for app
├── tsconfig.node.json     # TypeScript configuration for Node.js
├── tailwind.config.js     # Tailwind CSS configuration
├── postcss.config.js      # PostCSS configuration
├── dist/                  # Build output directory (generated)
└── src/                   # Source code directory
    ├── App.tsx            # Main application component
    ├── main.tsx           # Application entry point
    ├── index.css          # Global styles and Tailwind CSS imports
    ├── vite-env.d.ts      # Vite type definitions
    ├── api/               # API related code
    ├── assets/            # Static assets
    ├── components/        # Reusable components
    ├── layouts/           # Layout components
    ├── pages/             # Page components
    ├── store/             # State management
    ├── styles/            # Style files
    └── types/             # TypeScript type definitions
```

### Code Organization Principles

- Write semantic React components with clear component hierarchy
- Use TypeScript interfaces and types to ensure type safety
- Create modular components with clear separation of concerns
- Prioritize maintainability and readability

## Tech Stack

### Core Framework
- **React**: 18.3.1 - Declarative UI library
- **TypeScript**: 5.8.3 - Type-safe JavaScript superset
- **Vite**: 7.0.0 - Next generation frontend build tool
- **Tailwind CSS**: 3.4.17 - Atomic CSS framework

### Component Library
- **shadcn/ui**: Pre-built, accessible components built on Radix UI primitives
- **Radix UI**: Unstyled, accessible UI primitives
- **class-variance-authority**: Variant-based component styling
- **tailwind-merge**: Intelligent Tailwind class merging
- **lucide-react**: Beautiful, consistent icons

### Routing and State Management
- **React Router DOM**: 6.30.1 - Client-side routing
- **Zustand**: 4.4.7 - Lightweight state management

### Form Handling & Validation
- **Zod**: 3.25.76 - TypeScript-first schema validation
- **React Hook Form**: Efficient form handling (ready to integrate)

### Error Tracking & Monitoring
- **Sentry**: Production error tracking and performance monitoring
- **Browser tracing**: Performance monitoring
- **Session replay**: User session recording for debugging

### Internationalization Support
- **i18next**: 23.10.1 - Internationalization core library
- **react-i18next**: 14.1.0 - React integration for i18next
- **i18next-browser-languagedetector**: 7.2.0 - Browser language detection

### UI and Styling
- **Framer Motion**: 11.0.8 - Powerful animation library
- **GSAP**: 3.13.0 - High-performance professional animation library
- **clsx**: 2.1.0 - Conditional className utility

### 3D Graphics and Physics
- **Three.js**: 0.179.1 - JavaScript 3D graphics library
- **Cannon-es**: Modern TypeScript-enabled 3D physics engine
- **Matter.js**: 0.20.0 - 2D physics engine for web

## Technical Standards

### React Component Development Methodology

- Use functional components and React Hooks
- Implement single responsibility principle for components
- Create reusable and composable component architecture
- Use TypeScript for strict type checking

### Styling and Design System

- Use Tailwind CSS design token system
- Apply mobile-first responsive design approach
- Leverage modern layout techniques (Grid, Flexbox)
- Implement thoughtful animations and transitions through Framer Motion and GSAP
- Create immersive 3D visual experiences with Three.js
- Add realistic physics interactions using Cannon-es and Matter.js

### CSS Import Order Rules

**CRITICAL**: `@import` statements must come BEFORE all other CSS statements to avoid PostCSS warnings.

### State Management Approach

- Use Zustand for global state management
- Prioritize React built-in Hooks for local state
- Implement clear data flow and state update patterns
- Ensure state predictability and debugging capabilities

### Performance Optimization Requirements

- Use React.memo and useMemo for component optimization
- Implement code splitting and lazy loading
- Optimize resource loading and caching strategies
- Ensure all interactions work on both touch and pointer devices

## Development Commands

### Frontend (React Dashboard)
```bash
# Install dependencies
npm install

# Development server (http://localhost:5173)
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```

### Backend (ML Service)
```bash
cd ml-service

# Start with Docker Compose (Recommended)
docker-compose up -d

# Or run locally
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Train new model
python scripts/train_model.py /path/to/json/files --output-dir ./models

# Run tests
pytest tests/ -v --cov=app

# Access services
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000
```

## Project Architecture

### Frontend Structure
```
src/
├── App.tsx                 # Main app with routing logic
├── main.tsx               # React entry point
├── index.css              # Global styles + Tailwind
├── components/
│   ├── Navigation.tsx     # Top navigation bar
│   ├── StatCard.tsx       # Animated metric cards
│   └── RiskChart.tsx      # Risk distribution visualization
└── pages/
    ├── Dashboard.tsx      # Main dashboard with stats
    ├── PredictionForm.tsx # Patient prediction interface
    └── ModelMetrics.tsx   # Model performance metrics
```

### Backend Structure
```
ml-service/
├── app/
│   ├── main.py           # FastAPI application
│   ├── models.py         # Pydantic schemas
│   ├── ml_model.py       # Model wrapper & feature extraction
│   ├── feature_store.py  # Redis caching layer
│   ├── monitoring.py     # Prometheus metrics
│   └── config.py         # Settings management
├── models/               # Trained model artifacts
├── tests/               # Comprehensive test suite
├── Dockerfile           # Multi-stage production build
└── docker-compose.yml   # Full stack orchestration
```

### API Integration

The frontend is designed to connect to the FastAPI backend:
```typescript
// Example API call structure
const response = await fetch('http://localhost:8000/predict', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(patientData)
});
```

**Note**: Currently using mock data for demo. To connect to real backend:
1. Start ML service: `cd ml-service && docker-compose up -d`
2. Update API endpoints in frontend pages to point to `http://localhost:8000`

## Build and Deployment

The project uses Vite build system:
- **Development server**: `http://127.0.0.1:5173`
- **Build output**: `dist/` directory
- **Supports HMR**: Hot Module Replacement
- **Optimized production build**: Automatic code splitting and optimization

## Configuration Files

- `vite.config.ts` - Vite configuration
- `tsconfig.json` - TypeScript configuration
- `tailwind.config.js` - Tailwind CSS configuration
- `postcss.config.js` - PostCSS configuration
- `components.json` - shadcn/ui component configuration
- `yw_manifest.json` - Project manifest file

## Component Library (shadcn/ui)

This project uses [shadcn/ui](https://ui.shadcn.com/) - a collection of reusable components built with Radix UI and Tailwind CSS.

### Available Components

Located in [`src/components/ui/`](src/components/ui/):

- **Button** - Versatile button with multiple variants (default, destructive, outline, secondary, ghost, link)
- **Card** - Container component with header, title, description, content, and footer
- **Input** - Form input with focus states and validation support
- **Label** - Form label component
- **Dialog** - Modal dialog component with overlay and animations
- **Select** - Dropdown select component with search support
- **Toast** - Notification system with multiple variants

### Adding New Components

```bash
# Add a new component
npx shadcn-ui@latest add [component-name]

# Example: Add badge component
npx shadcn-ui@latest add badge
```

### Using Components

```tsx
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"

function Example() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Example Card</CardTitle>
      </CardHeader>
      <CardContent>
        <Button>Click me</Button>
      </CardContent>
    </Card>
  )
}
```

## Error Tracking (Sentry)

This project integrates [Sentry](https://sentry.io/) for production error tracking and performance monitoring.

### Setup

1. Create a Sentry account and get your DSN
2. Add your DSN to `.env`:
   ```bash
   VITE_SENTRY_DSN=your_sentry_dsn_here
   ```

### Usage

```tsx
import { captureException, addBreadcrumb, setSentryUser } from "@/lib/sentry"

// Track user actions
addBreadcrumb("User clicked button", "user", "info")

// Set user context
setSentryUser({ id: "123", email: "user@example.com" })

// Capture errors
try {
  // Your code
} catch (error) {
  captureException(error, { additionalContext: "value" })
}
```

### Features

- **Error Tracking**: Automatic error capture and reporting
- **Performance Monitoring**: Browser tracing for page load times
- **Session Replay**: Record user sessions for debugging
- **Breadcrumbs**: Track user actions leading to errors
- **User Context**: Associate errors with specific users

## Environment Variables

Copy [`.env.example`](.env.example) to `.env` and configure:

```bash
# Application
VITE_APP_NAME=IIT ML Service
VITE_APP_VERSION=1.0.0

# API
VITE_API_URL=http://localhost:8000

# Sentry (Optional - for production error tracking)
VITE_SENTRY_DSN=your_sentry_dsn_here

# Feature Flags
VITE_ENABLE_ERROR_TRACKING=false
```

See [`.env.example`](.env.example) for all available options.

## Development Setup

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+ (for backend)
- Docker (optional, for containerized deployment)

### Frontend Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Backend Setup

```bash
cd backend/ml-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn app.main:app --reload

# Or use Docker
docker-compose up -d
```

## Testing

```bash
# Run tests
npm test

# Run tests in watch mode
npm run test:watch

# Generate coverage report
npm run test:coverage

# Run E2E tests with Cypress
npx cypress open
```

## Deployment

### Vercel (Recommended)

1. Push code to GitHub
2. Import project in Vercel
3. Configure environment variables
4. Deploy

### Docker

```bash
# Build production image
docker build -t iit-ml-service .

# Run container
docker run -p 5173:5173 iit-ml-service
```

### Manual Deployment

```bash
# Build for production
npm run build

# The dist/ folder contains your production build
# Deploy dist/ to your hosting service
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Use TypeScript for type safety
- Follow existing component patterns
- Use shadcn/ui components when possible
- Write meaningful commit messages
- Add tests for new features

### Project Structure Guidelines

```
src/
├── components/
│   ├── ui/              # shadcn/ui components (don't modify)
│   └── [feature]/       # Feature-specific components
├── lib/                 # Utility functions
├── hooks/               # Custom React hooks
├── pages/               # Page components
├── contexts/            # React contexts
├── services/            # API services
└── types/               # TypeScript types
```

## Roadmap

### Completed ✅
- [x] shadcn/ui component library integration
- [x] Sentry error tracking setup
- [x] Environment variable management
- [x] TypeScript path aliases (`@/`)

### In Progress 🚧
- [ ] React Hook Form + Zod integration
- [ ] Clerk/Supabase authentication
- [ ] PostHog/Plausible analytics

### Planned 📋
- [ ] File upload integration (Upload Thing/Cloudinary)
- [ ] Vercel deployment configuration
- [ ] Performance monitoring with Lighthouse
- [ ] Empty states and onboarding flows

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review the code comments and type definitions
