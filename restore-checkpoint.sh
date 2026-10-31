#!/bin/bash
# Script to restore the exact telemetry-ui checkpoint state
set -e
echo "Restoring telemetry-ui checkpoint..."
cp .checkpoints/telemetry-ui/dashboard-page.svelte frontend/src/routes/dashboard/+page.svelte
cp .checkpoints/telemetry-ui/app.css frontend/src/app.css
cp .checkpoints/telemetry-ui/app.html frontend/src/app.html
cp .checkpoints/telemetry-ui/layout.svelte frontend/src/routes/+layout.svelte
cp .checkpoints/telemetry-ui/landing-page.svelte frontend/src/routes/+page.svelte
cp .checkpoints/telemetry-ui/AssistantPanel.svelte frontend/src/lib/components/AssistantPanel.svelte
cp .checkpoints/telemetry-ui/Stat.svelte frontend/src/lib/components/Stat.svelte
cp .checkpoints/telemetry-ui/StatusBadge.svelte frontend/src/lib/components/StatusBadge.svelte
cp .checkpoints/telemetry-ui/assistant.py backend/app/services/ai_engine/assistant.py
cp -r .checkpoints/telemetry-ui/static frontend/
echo "Restored successfully!"
