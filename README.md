# Backend (Django + Channels)

## Setup

1. Create environment:
   - `python -m venv .venv`
   - `.\.venv\Scripts\activate` (Windows)
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Configure environment:
   - copy `.env.example` to `.env`
4. Run migrations:
   - `python manage.py makemigrations`
   - `python manage.py migrate`
5. Start server:
   - `python manage.py runserver`

## Key Modules

- `apps/game/models.py`: room, player, question, answer, guess, sync result schema
- `apps/game/services.py`: game lifecycle and scoring logic
- `apps/game/consumers.py`: websocket consumer for live updates
- `apps/ai/services/embedding.py`: multilingual embedding + cosine similarity
