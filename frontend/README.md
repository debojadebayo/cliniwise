# CliniWise Frontend

The frontend for CliniWise, a modern clinical guidelines management system. Built with React, TypeScript, and Next.js.

## 🏗️ Architecture

The frontend is organized into several key components:

### 📱 Main Routes

1. `/` - Home/Landing Page

   - Document selector for clinical guidelines
   - Overview of available medical documentation

2. `/conversation/{conversation_id}`
   - Interactive chat window for querying documents
   - PDF viewer with highlighting capabilities
   - Real-time conversation history

### 🧩 Key Components

- `pdf-viewer/`

  - `ViewPdf.tsx`: Main PDF rendering component
  - `PdfOptionsBar.tsx`: Controls for PDF navigation and interaction

- `conversations/`

  - `RenderConversations.tsx`: Chat interface for document interactions
  - `MessageComponent.tsx`: Individual message rendering

- `common/`
  - Reusable UI components
  - Shared utilities and hooks

## 🚀 Getting Started

### Prerequisites

- Node.js 16 or later
- npm or yarn
- Backend services running (see main README)

### Installation

1. Install dependencies:

   ```bash
   npm install
   ```

2. Start the development server:

   ```bash
   npm run dev
   ```

3. Access the application at:
   ```
   http://localhost:3000
   ```

## 💻 Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run lint` - Run ESLint
- `npm run test` - Run tests
- `npm run preview` - Preview production build

### Code Style

- TypeScript for type safety
- ESLint + Prettier for code formatting
- Component-based architecture
- CSS Modules with Tailwind CSS

### Best Practices

1. **Components**

   - Use functional components with hooks
   - Keep components small and focused
   - Implement proper error boundaries

2. **State Management**

   - Context API for global state
   - Local state for component-specific data

3. **Performance**
   - Lazy loading for routes
   - Memoization where appropriate
   - Optimized PDF rendering

## 📦 Building for Production

```bash
# Create production build
npm run build

# Preview production build
npm run preview
```

## 🔗 API Integration

The frontend communicates with the backend through:

- REST API endpoints for data operations
- WebSocket connections for real-time updates
- S3 for PDF document access

## 🎨 UI/UX Guidelines

- Modern, clean interface
- Responsive design for all screen sizes
- Accessibility compliance
- Consistent color scheme and typography

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📚 Resources

- [React Documentation](https://react.dev/)
- [TypeScript Documentation](https://www.typescriptlang.org/)
- [Nextjs Documentation](https://nextjs.org/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)
