#!/bin/bash

#!/bin/bash

# Simple setup for native installation
echo "Setting up Web Scraper..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Remove old virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Removing old virtual environment..."
    rm -rf .venv
fi

# Create fresh virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip first
echo "Upgrading pip..."
python -m ensurepip --upgrade
python -m pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create output directory
mkdir -p output

# Create simple launcher
cat > launch.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
python main.py
EOF

chmod +x launch.sh

echo "Setup complete!"
echo ""
echo "To run the scraper:"
echo "  ./launch.sh"