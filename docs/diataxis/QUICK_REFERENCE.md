# Babylon Documentation Quick Reference

## 🚀 I'm New Here
- **Install & Run**: [Getting Started](tutorials/getting-started.md) 
- **Learn to Play**: [First Game Session](tutorials/first-game-session.md)
- **Set Preferences**: [Basic Configuration](tutorials/basic-configuration.md)

## 🛠️ I Need to Fix Something  
- **Game Won't Start**: [Troubleshooting → Installation Issues](how-to/troubleshooting.md#installation-and-setup-issues)
- **Poor Performance**: [Troubleshooting → Runtime Issues](how-to/troubleshooting.md#runtime-issues)
- **ChromaDB Problems**: [Configure ChromaDB](how-to/configure-chromadb.md)
- **AI Not Working**: [Troubleshooting → AI System](how-to/troubleshooting.md#ai-system-not-responding)

## 🧑‍💻 I Want to Contribute
- **Set Up Dev Environment**: [Development Setup](how-to/development-setup.md)
- **Understand the Code**: [Architecture Overview](explanation/architecture.md)
- **Learn the Philosophy**: [Design Philosophy](explanation/design-philosophy.md)

## 📖 I Need Reference Info
- **All Settings**: [Configuration Reference](reference/configuration.md)  
- **API Documentation**: [API Reference](reference/api/)
- **Error Codes**: [Reference → Error Codes](reference/error-codes.md)

## 💡 I Want to Understand the Concepts
- **How It's Built**: [Architecture Overview](explanation/architecture.md)
- **Why These Choices**: [Design Philosophy](explanation/design-philosophy.md)  
- **Theory Behind the Game**: [Dialectical Materialism](explanation/dialectical-materialism.md)

## 🆘 Emergency Commands

```bash
# Quick start
python -m babylon

# Diagnostics  
python -m babylon --diagnose

# Reset everything
rm -rf ./data/chroma
python -m babylon --init-all --force

# Get help
python -m babylon --help
```

## 📁 Documentation Structure

```
docs/diataxis/
├── tutorials/          # Learning-oriented
│   ├── getting-started.md
│   ├── first-game-session.md  
│   └── basic-configuration.md
├── how-to/            # Problem-oriented  
│   ├── configure-chromadb.md
│   ├── development-setup.md
│   └── troubleshooting.md
├── reference/         # Information-oriented
│   ├── configuration.md
│   └── api/
└── explanation/       # Understanding-oriented
    ├── architecture.md
    ├── design-philosophy.md
    └── dialectical-materialism.md
```

---

**📍 Start here**: [Complete Documentation Index](index.md)