# Babylon Project Constraints

You are working on Babylon, a political simulation engine with a Django + React web architecture. These rules are non-negotiable. Violations must be flagged immediately, not worked around silently.

## Import Boundary

Engine code (`src/babylon/`) NEVER imports Django. Django code (`web/`) accesses the engine ONLY through `engine_bridge.py`. If you find yourself importing `babylon.engine` in a Django view, stop and route it through the bridge.

## State Architecture

WorldState is frozen Pydantic. Changes happen via `model_copy()`. No mutable state objects. No database I/O during tick execution — Postgres is the persistence layer, not the computation layer.

## JSON Everywhere

The API serves JSON. The engine bridge produces JSON. Postgres stores JSONB. React consumes JSON. If something isn't JSON-serializable, fix the serialization.

## No Magic Constants

Every coefficient, threshold, AP cost, and tuning parameter lives in GameDefines with documented provenance. Nothing hardcoded in views, serializers, components, or templates.

## Data Separation

Material conditions come from federal statistical data (QCEW, BEA, Census, FRED, ATUS, LODES). Strategic choices come from the player. The frontend never computes derived economic quantities — those are engine outputs.

## Test Case

Detroit tri-county: Wayne (26163), Oakland (26125), Macomb (26099). If it doesn't work for tri-county Detroit, it doesn't work. Wayne = deindustrializing core (lower profit rate, higher heat). Oakland = financialized suburb (higher profit rate, lower heat). Macomb = bellwether (middle).

## Visual Design

Constitutional color palette only. BLOOD_VOID (#1a0005), BLACK (#0d0d0d), CRIMSON (#8b0000), GOLD (#daa520), SILVER (#c0c0c0), ASH (#808080). Luminosity encodes magnitude. No decorative color. Dark background, light-on-dark text.

## Edge Modes Are Categorical

Five modes: EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC, CO-OPTIVE. Display as discrete badges, never as scalar bars or gradients. Transitions follow a state machine with required intermediates.

## Organizations Are Agents

Not individuals, not demographic blocks. Four subtypes: StateApparatus, Business, PoliticalFaction, CivilSocietyOrg. All player verbs operate through organizations.

## Feature 037 Owns the Simulation Schema

Django ORM manages GameSession, PlayerAction, ActionResult only. Everything else — simulation state, graph persistence, hex data, community consciousness — goes through Feature 037's raw SQL layer. Do not duplicate table definitions.

## SQLite Reference Database Is Read-Only

Never write to it. It contains calibrated federal statistical data. It initializes simulations but is never modified during play.
