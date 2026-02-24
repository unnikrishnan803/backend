# 🚀 Hosting Your Django Backend on Render

Your backend is already well-configured for Render. It uses `daphne` for websockets/ASGI, `dj_database_url` for parsing database strings, and `whitenoise` for static files.

Follow these step-by-step instructions to deploy your backend to Render.com.

## Step 1: Push Your Code to GitHub
Ensure all your backend code (including `build.sh` and `Procfile`) is pushed to a GitHub repository.

## Step 2: Create a PostgreSQL Database
1. Go to your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** and select **PostgreSQL**.
3. Give it a name (e.g., `romutoo-db`).
4. Select the Free instance type (or whichever you prefer).
5. Click **Create Database**.
6. Once created, copy the **Internal Database URL** (you'll need this later).

## Step 3: Create a Redis Instance (For WebSockets/Channels)
Since your app uses Django Channels for WebSockets, you'll need Redis.
1. Click **New +** again on the Render Dashboard and select **Redis**.
2. Give it a name (e.g., `romutoo-redis`).
3. Select the Free instance type instance.
4. Click **Create Redis**.
5. Once created, copy the **Internal Redis URL** (you'll need this later).

## Step 4: Create the Web Service (Your Backend)
1. Click **New +** and select **Web Service**.
2. Connect your GitHub repository containing the backend code.
3. Choose a name (e.g., `romutoo-backend`).
4. **Environment**: Select `Python`.
5. **Build Command**: Set this to `bash build.sh`
6. **Start Command**: Set this to `daphne config.asgi:application --port $PORT --bind 0.0.0.0`
7. Choose the Free instance type.

## Step 5: Configure Environment Variables
Before clicking "Create Web Service", scroll down to **Environment Variables** and add the following keys:

| Key | Value |
| :--- | :--- |
| `PYTHON_VERSION` | `3.10.0` *(or your Python version)* |
| `DATABASE_URL` | *(Paste the Internal Database URL from Step 2)* |
| `REDIS_URL` | *(Paste the Internal Redis URL from Step 3)* |
| `DJANGO_SECRET_KEY` | *(Create a long, random securely generated string)* |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `*` *(or your Render web service domain like `romutoo-backend.onrender.com`)* |
| `FRONTEND_ORIGIN` | *(The URL of your deployed frontend, e.g., `https://romutoo.vercel.app` - Or `*` for all)* |

## Step 6: Deploy
1. Click **Create Web Service**.
2. Render will now build your project using `build.sh`. This process will install requirements, collect static files, and run database migrations automatically.
3. Once the build is successful, you will see a green **Live** status and you can find your live URL at the top left (i.e. `https://romutoo-backend-xxxx.onrender.com`).

---

### Basic Debugging Tips
- If the build fails, check the "Logs" tab on Render to see what `build.sh` outputted.
- If it complains about `build.sh` not having permissions, that's why we used `bash build.sh` as the build command!
- Make sure `requirements.txt` is updated if you add any new packages.
