// frontend/tests/fixtures/paridad_oportunidad.js
//
// Fixture de paridad Python↔JS para el índice de oportunidad (F-4 de
// `correccion/avance_plan.md`, punto 30.iii; docs/metodologia.md §10.2 nota final).
//
// Los mismos vectores de entrada y el mismo `esperado` viven, literalmente iguales, en
// `backend/tests/test_features.py::TestParidadIndiceOportunidadPythonJs`. Si alguien cambia
// la fórmula de un lado (`features.indice_oportunidad` o `composicion.indiceOportunidad`) sin
// tocar el otro, una de las dos pruebas falla -- ese es el propósito: evitar que las dos
// implementaciones se separen en silencio. Si de verdad hay que cambiar la fórmula, hay que
// recalcular `esperado` y actualizar AMBOS archivos a mano en el mismo cambio.
//
// Casos cubiertos: cobertura 0 (máxima oportunidad), cobertura alta, tasas iguales (ajuste 0),
// `NaN` (sin_datos, se propaga), ajuste positivo y negativo saturado (`clip` a ±0.15), y
// cobertura muy alta con tasa de oferta mucho mayor (saturación del lado bajo).

export const FIXTURE_PARIDAD_OPORTUNIDAD = {
  k: 5.0,
  cobertura: [0.0, 1000.0, 500.0, NaN, 250.0, 4000.0, 0.0],
  tasaDemanda: [-3.0, -3.0, 2.0, -3.0, 0.0, -5.0, 1.0],
  tasaOferta: [-1.0, -1.0, 2.0, -1.0, 5.0, -6.0, -4.0],
  esperado: [0.75, 0.05, 0.4, NaN, 0.45, 0.15, 1.0],
};
