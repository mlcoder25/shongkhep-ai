#!/bin/bash

# ─── Shongkhep AI — One-click startup script ──────────────────────────────────

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting Shongkhep AI..."
echo ""

# ── Step 1: Start Docker (backend + redis + postgres) in background ────────────
echo "🐳 Starting backend services (Docker)..."
cd "$PROJECT_DIR"
docker compose up --build -d

echo ""
echo "⏳ Waiting for backend to be ready..."
sleep 10

# ── Step 2: Check backend health ───────────────────────────────────────────────
HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null)
if echo "$HEALTH" | grep -q "ok"; then
    echo "✅ Backend is running!"
else
    echo "⚠️  Backend still starting up — this is normal, please wait..."
fi

echo ""

# ── Step 3: Install frontend packages if needed ────────────────────────────────
cd "$PROJECT_DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend packages (first time only)..."
    npm install
fi

# ── Step 4: Start frontend ─────────────────────────────────────────────────────
echo ""
echo "🌐 Starting frontend at http://localhost:3000"
echo ""
echo "────────────────────────────────────────────────"
echo "  App:        http://localhost:3000"
echo "  API Docs:   http://localhost:8000/docs"
echo "  Grafana:    http://localhost:3001  (admin/grafanapass)"
echo "  Flower:     http://localhost:5555  (admin/flowerpass)"
echo "────────────────────────────────────────────────"
echo ""
echo "Press Ctrl+C to stop the frontend."
echo "To stop backend: docker compose down"
echo ""

npm run dev
