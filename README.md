# 🏥 CliniWise

A modern, AI-powered clinical guidelines management system that helps healthcare professionals access and interact with medical documentation efficiently.


## 🌟 Features

- Template of the application is very heavily inspired from the SEC insights repo (https://github.com/run-llama/sec-insights)

- **🤖 AI-Powered Interactions**
  - Natural language querying of medical documents
  - Context-aware responses based on document content
  - Intelligent document summarization

- **🔍 Advanced Search**
  - Full-text search across all documents
  - Semantic similarity matching
  - Filter by document type and metadata

- **👥 User-Friendly Interface**
  - Modern, responsive web interface
  - PDF viewer with highlighting
  - Intuitive conversation interface

- Examples guidelines uploaded to application for you to get started with

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.10 or later
- Node.js 16 or later
- Poetry (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/cliniwise.git
   cd cliniwise
   ```

2. **Set up the backend**
   ```see README.md backend  # Configure your environment variables
   ```

3. **Set up the frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Start the services**
   ```bash
   # In the backend directory
   docker-compose up -d
   make migrate
   make run
   
   # In a new terminal, frontend directory
   npm run dev
   ```

5. **Initialize the database**
   ```bash
   make seed_db_local
   ```

## 🏗️ Architecture

CliniWise is built with a modern tech stack:

- **Frontend**: React, TypeScript, Vite
- **Backend**: FastAPI, PostgreSQL, pgvector
- **AI/ML**: LlamaIndex for document processing and embeddings
- **Storage**: S3-compatible storage (LocalStack for development)

## 📝 Development

### Local Development Setup

1. Start the local services:
   ```bash
   make run
   ```

2. Seed the database with example clinical guidelines:
   ```bash
   make seed_db_local
   ```

3. Access the application:
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Environment Variables

Key environment variables:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/llama_app_db
S3_ENDPOINT_URL=http://localhost:4566
S3_ASSET_BUCKET_NAME=clinical-guidelines-assets
OPENAI_API_KEY=your-api-key
```

## 🤝 Contributing

I welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [LlamaIndex](https://github.com/jerryjliu/llama_index)
- PDF processing powered by [PyMuPDF](https://github.com/pymupdf/PyMuPDF)
- Very heavily inspired from the SEC insights repo (https://github.com/run-llama/sec-insights)