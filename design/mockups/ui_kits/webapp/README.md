# Babylon Web App UI Kit

High-fidelity recreation of the Babylon web application UI.

**Design system:** Bunker Constructivism — "Damp Basement Cyberinsurgency"  
**Stack (source):** React 18 + TypeScript + Tailwind CSS v4 + Lucide React  
**Stack (kit):** React 18 + Babel JSX + inline CSS vars from colors_and_type.css

## Screens

1. **Login** — BABYLON wordmark, username/password form, gradient void background
2. **Game List** — nav bar, game cards with scenario selector, create new game button
3. **Game Shell** — full viewport: TopBar → ResourceBar → Map placeholder → LensBar → BottomPanel → RightPanel (ActionComposer)
4. **Action Page** — full-page verb form (educate / attack / aid / mobilize)

## Component Files

| File | Contents |
|---|---|
| `Login.jsx` | LoginPage component |
| `GameList.jsx` | GameList component with nav |
| `GameShell.jsx` | Full game dashboard shell |
| `ActionPage.jsx` | Verb action form |
| `index.html` | Interactive click-through prototype |

## Usage

Open `index.html` in a browser. All screens are wired together:
- Login → Game List → Game Shell → Action Page

Components use only CDN dependencies (React, Babel, Lucide).
