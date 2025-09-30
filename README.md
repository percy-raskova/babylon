# The Fall of Babylon

*The Fall of Babylon* is a text-based role-playing game (RPG) that simulates complex social, political, and economic systems using XML data structures and AI components. The game incorporates Marxist theory and dialectical materialism to model contradictions and societal changes.

## Table of Contents
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Introduction](#introduction)
- [Project Structure](#project-structure)
- [Game Mechanics](#game-mechanics)
- [AI Integration](#ai-integration)
- [Contributing](#contributing)
- [License](#license)

## Quick Start
**Want to contribute?** See the [Development Setup Guide](docs/diataxis/how-to/development-setup.md)
**Need help?** Check the [Troubleshooting Guide](docs/diataxis/how-to/troubleshooting.md)


## Documentation
Our documentation follows the [Diataxis framework](https://diataxis.fr/) for better organization:

### 📚 [**Tutorials**](docs/diataxis/tutorials/) - Learn by doing
- [Getting Started](docs/diataxis/tutorials/getting-started.md) - Install and run your first game
- [First Game Session](docs/diataxis/tutorials/first-game-session.md) - Complete gameplay walkthrough  
- [Basic Configuration](docs/diataxis/tutorials/basic-configuration.md) - Customize your setup

### 🛠️ [**How-to Guides**](docs/diataxis/how-to/) - Solve specific problems
- [Configure ChromaDB](docs/diataxis/how-to/configure-chromadb.md) - Set up vector database
- [Development Setup](docs/diataxis/how-to/development-setup.md) - Prepare for contributing
- [Troubleshooting](docs/diataxis/how-to/troubleshooting.md) - Fix common issues

### 📖 [**Reference**](docs/diataxis/reference/) - Look up details  
- [Configuration Reference](docs/diataxis/reference/configuration.md) - All settings explained
- [API Reference](docs/diataxis/reference/api/) - Technical specifications

2. **Set Up Directory Structure**

   ```shell
   mkdir -p data/metrics
   mkdir -p logs/metrics
   mkdir -p backups
   mkdir -p chroma
   mkdir -p data/metrics
   mkdir -p logs/metrics
   mkdir -p backups
   mkdir -p chroma
   ```
3. **Create and Activate Virtual Environment**

   ```shell
   python -m venv venv
   source venv/bin/activate  # On Windows use venv\Scripts\activate
   ```
   
4. **Install Dependencies**

   ```shell
   pip install -r requirements.txt
   ```

5. **Configure Environment**

   Copy `.env.example` to `.env`:

   ```shell
   cp .env.example .env
   ```

   Update the values in `.env` with your configuration.

6. **Initialize Databases**


   - Set up PostgreSQL database
   - Initialize ChromaDB storage
   - Configure metrics collection

   Refer to [CONFIGURATION.md](docs/CONFIGURATION.md) for detailed setup instructions.

## AI Integration

### ChromaDB Vector Database
- **Entity Storage**: Efficient vector representations
- **Similarity Search**: Fast kNN queries
- **Persistence**: DuckDB+Parquet backend
- **Performance**:
  - Query response < 100ms
  - Memory optimization
  - Cache management
  - Automatic backups

### Metrics Collection
- Real-time performance monitoring
- Gameplay pattern analysis
- System resource tracking
- Cache performance optimization

## Error Handling & Logging

### Error Management

- Structured error codes by subsystem
- Comprehensive error tracking
- Automatic error recovery
- Detailed error context

### Logging System

- JSON-structured logging
- Multiple log streams
- Automatic rotation
- Performance metrics
- Error context capture

For complete documentation:
- [ERROR_CODES.md](docs/ERROR_CODES.md)
- [LOGGING.md](docs/LOGGING.md)

### Current Features

- Entity embeddings via SentenceTransformer
- Contradiction relationship analysis
- Dynamic event generation
- Performance metrics collection
- Pre-embeddings system with:
  - Content preprocessing and normalization
  - Intelligent content chunking
  - Embedding cache management
  - Integration with lifecycle management

### Planned Features

- Enhanced NPC behaviors
- Advanced decision systems
- Natural language processing
- Dynamic world generation
- Context window management
- Priority queuing for object lifecycle

For implementation details, see [CHROMA.md](docs/CHROMA.md).

## License

MIT License - see [LICENSE](LICENSE).

For detailed progress and updates, see [CHANGELOG.md](docs/CHANGELOG.md).
