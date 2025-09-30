# Getting Started with Babylon

Welcome to Babylon! This tutorial will guide you through installing and running your first game session. By the end, you'll have Babylon running on your system and understand the basic game concepts.

## What You'll Learn

- How to install Babylon and its dependencies
- How to configure the basic settings  
- How to start your first game session
- Basic game mechanics and controls

## Prerequisites

Before starting, make sure you have:
- Python 3.12 or higher
- PostgreSQL 13 or higher
- At least 4GB of available disk space
- A stable internet connection for downloading dependencies

## Step 1: Clone the Repository

Open your terminal and run:

```bash
git clone https://github.com/bogdanscarwash/babylon.git
cd babylon
```

## Step 2: Set Up Your Environment

### Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note**: Installation may take a few minutes as it downloads AI models and other dependencies.

## Step 3: Initial Configuration

### Create Your Environment File

Copy the example environment file:

```bash
cp .env.example .env
```

### Edit Basic Settings

Open the `.env` file in your text editor and set these essential values:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/babylon

# AI Integration (optional for first run)
OPENAI_API_KEY=your_openai_key_here

# Game Settings
GAME_DIFFICULTY=normal
AUTO_SAVE=true
```

> **Tip**: You can start without an OpenAI API key - the game will use simplified AI behavior.

## Step 4: Initialize the Game Database

Run the setup script to prepare your game database:

```bash
python -m babylon.setup --init
```

This will:
- Create necessary database tables
- Set up the vector database (ChromaDB)
- Initialize basic game data

## Step 5: Start Your First Game Session

Now you're ready to play! Start the game with:

```bash
python -m babylon
```

You should see the game welcome screen:

```
================================
    WELCOME TO BABYLON
================================

Starting new game session...
Loading world data...
Initializing AI systems...

> 
```

## Step 6: Basic Game Commands

Try these commands to get familiar with the game:

- `help` - Show available commands
- `status` - View current game state
- `look` - Examine your surroundings  
- `inventory` - Check your resources
- `quit` - Exit the game safely

Example session:
```
> status
=== GAME STATUS ===
Year: 2024
Population: 10,000
Economic Stability: 75%
Political Tension: Medium

> look
You are in the Central District of New Babylon.
Economic contradictions are building between the merchant class and workers.
Political unrest simmers beneath the surface.

> help
Available commands:
- status: View current game state
- look: Examine surroundings
- act [decision]: Make a political/economic decision
- history: View recent events
- save: Save your progress
- quit: Exit game
```

## What You've Accomplished

Congratulations! You've successfully:

✅ Installed Babylon and its dependencies
✅ Configured your basic game settings
✅ Started your first game session
✅ Learned the basic game commands

## Next Steps

Now that you have Babylon running, you might want to:

- **Play your first full session**: Try the [First Game Session](first-game-session.md) tutorial
- **Customize your setup**: Learn about [Basic Configuration](basic-configuration.md)
- **Understand the mechanics**: Read about [Game Concepts](../explanation/game-concepts.md)

## Troubleshooting

**Game won't start?**
- Check that PostgreSQL is running
- Verify your database connection in `.env`
- See [Troubleshooting Guide](../how-to/troubleshooting.md)

**Performance issues?**
- Reduce AI complexity in settings
- Check system requirements
- See [Performance Tuning](../how-to/performance-tuning.md)

---

**Need help?** Check out the [How-to Guides](../how-to/) or [Reference Documentation](../reference/) for more detailed information.