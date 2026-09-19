# Makefile mínimo de chipos_dataton. Uso: make perfil | pipeline | test | serve
PY ?= .venv/bin/python
PUERTO ?= 8000

.PHONY: perfil pipeline test serve censo datos descargas vendor-d3

# Descarga fuentes oficiales y extrae la CDMX a data/processed/ (no sobrescribe)
descargas:
	$(PY) tools/descargar_datos.py

# Derivados en data/interim/ y data/reference/ageb_cdmx*.geojson
datos: censo
	$(PY) tools/build_censo.py
	$(PY) tools/build_conapo.py
	$(PY) tools/build_geo.py

# xlsx del equipo → parquet (solo contraste; el 2010 está truncado)
censo:
	$(PY) tools/convertir_censo.py

# Perfil acotado de los datos → docs/perfil_datos.md
perfil: datos
	$(PY) tools/profile_data.py

# Regenera data/outputs/ (el paquete backend aún no existe; falla con mensaje claro)
pipeline: datos
	@test -d backend/src/chipos || { echo "backend/src/chipos no existe todavía (fase de implementación)"; exit 1; }
	PYTHONPATH=backend/src $(PY) -m chipos.exportar

test:
	@test -d backend/tests || { echo "backend/tests no existe todavía"; exit 1; }
	PYTHONPATH=backend/src $(PY) -m pytest -q backend/tests

# Servidor estático del frontend (sin build)
serve:
	@test -d frontend || { echo "frontend/ no existe todavía"; exit 1; }
	$(PY) -m http.server $(PUERTO) --directory frontend

# Regenera frontend/vendor/d3/d3-chipos.esm.js con esbuild (offline, puntual).
# Ver frontend/vendor/d3/README.md para el detalle del comando.
vendor-d3:
	cd frontend/vendor/d3 && npm install && node build.mjs && rm -rf node_modules package-lock.json
