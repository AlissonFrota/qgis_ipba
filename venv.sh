python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install numpy>1.0.0 wheel setuptools>=67
python -m pip install --no-cache --force-reinstall gdal[numpy]=="$(gdal-config --version).*"
deactivate
