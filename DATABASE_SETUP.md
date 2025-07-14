# Database Setup Guide for Render Deployment

## Overview
This guide explains how to set up a PostgreSQL database on Render to persist conversation history across deployments.

## Important Note: Python 3.13 Compatibility
This application uses `psycopg3` (psycopg[binary]) for PostgreSQL connections, which is compatible with Python 3.13. The older `psycopg2` package has known compatibility issues with Python 3.13.

## Step 1: Create PostgreSQL Database on Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "PostgreSQL"
3. Configure the database:
   - **Name**: `becqsight-db` (or your preferred name)
   - **Database**: `becqsight_db`
   - **User**: `becqsight_user`
   - **Region**: Choose the same region as your web service
   - **PostgreSQL Version**: 15 (or latest)
   - **Plan**: Free (for development) or paid plan for production

4. Click "Create Database"

## Step 2: Get Database Connection String

Once created, Render provides:
- **Internal Database URL** (for services in same region)
- **External Database URL** (for external connections)

Copy the **Internal Database URL** - it looks like:
```
postgresql://becqsight_user:password@dpg-xxxxx-a.oregon-postgres.render.com/becqsight_db
```

## Step 3: Configure Environment Variables

1. Go to your web service on Render
2. Go to "Environment" tab
3. Add/Update environment variable:
   - **Key**: `DATABASE_URL`
   - **Value**: Paste the Internal Database URL from Step 2

## Step 4: Deploy and Verify

1. Deploy your application
2. Check database health: `https://your-app.onrender.com/database-health`
3. Check overall health: `https://your-app.onrender.com/health`

## Database Endpoints

- `/database-health` - Database health status
- `/health` - Overall application health (includes database)
- `/admin/users` - User management (admin only)

## Troubleshooting

### Connection Issues
- Ensure the database is in the same region as your web service
- Use the Internal Database URL, not External
- Check that `DATABASE_URL` environment variable is set correctly
- The app automatically uses `psycopg3` for PostgreSQL connections

### Python 3.13 Compatibility
- If you see `psycopg2` import errors, ensure `psycopg[binary]` is in requirements.txt
- The app automatically falls back to `psycopg2` if `psycopg3` is not available

### Schema Issues
- The app automatically creates tables on first run
- Check `/database-health` endpoint for detailed status

### Performance Issues
- Free PostgreSQL has connection limits
- Consider upgrading to paid plan for production use

## Local Development

For local development, the app will use SQLite by default. To use PostgreSQL locally:

1. Install PostgreSQL locally
2. Set `DATABASE_URL` environment variable to your local PostgreSQL instance
3. Run the application

## Migration from SQLite to PostgreSQL

If you're migrating from SQLite to PostgreSQL:

1. Export your data from SQLite (if needed)
2. Set up PostgreSQL database on Render
3. Update `DATABASE_URL` environment variable
4. Deploy - the app will automatically create the schema
5. Import your data (if needed)

## Backup and Recovery

Render provides automatic backups for PostgreSQL databases:
- Free plan: Daily backups
- Paid plans: More frequent backups

You can also manually backup your data using the Render dashboard. 