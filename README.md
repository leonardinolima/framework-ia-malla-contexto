# Framework de desarrollo aumentado con IA — MVP

Prototipo académico de **malla de contexto y trazabilidad**. Incluye interfaz web, API HTTP y SQLite. No requiere instalar paquetes externos.

## Ejecutar

Requiere Python 3.10+.

```bash
python app.py
```

Abrir http://127.0.0.1:8000 y seguir los pasos: crear proyecto, cargar transcripción, extraer requisitos y generar historia, arquitectura y prueba. Los artefactos se enlazan por `source_id` y se almacenan en `mesh.sqlite3`.

## IA real (opcional)

Sin configurar un modelo, la aplicación genera **plantillas deterministas**, no resultados de IA. Para activar generación con un servicio OpenAI-compatible, definir variables de entorno antes de ejecutar:

```bash
export LLM_API_KEY='TU_CLAVE'
export LLM_BASE_URL='https://api.openai.com/v1'
export LLM_MODEL='gpt-4o-mini'
python app.py
```

En Windows PowerShell usar `$env:LLM_API_KEY="..."` y análogos. No publicar claves en GitHub.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

## API

- `POST /api/projects` `{ "name": "..." }`
- `GET /api/projects`
- `POST /api/projects/{id}/artifacts` `{ "text": "transcripción" }`
- `GET /api/projects/{id}/artifacts`
- `POST /api/artifacts/{id}/generate` `{ "kind": "story|architecture|test" }`

## Alcance y límites

Esto es un **MVP ejecutable**, no una validación TRL 5. La extracción de requisitos usa reglas heurísticas; la malla se modela como enlaces entre artefactos en SQLite. Para sustentar TRL 5 se requieren integración con un LLM real, evaluación en entorno relevante, métricas, pruebas con evidencia y demostración grabada. El prototipo corre en localhost y no implementa autenticación: no desplegar públicamente ni introducir información sensible real.

## GitHub

```bash
git init
git add .
git commit -m "MVP de malla de contexto"
git branch -M main
git remote add origin https://github.com/USUARIO/REPOSITORIO.git
git push -u origin main
```

Crear primero un repositorio vacío en GitHub y sustituir USUARIO/REPOSITORIO. Excluir `mesh.sqlite3` y `.env` mediante `.gitignore`.
