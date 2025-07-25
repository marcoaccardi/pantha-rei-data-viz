# Panta Rhei Data Map Project

## Project Structure
This is an ocean data visualization project with:
- `backend/` - Python backend using uv for virtual environment management
- `frontend/` - React/TypeScript frontend
- `ocean-data/` - Data storage directory at `/Volumes/Backup/panta-rhei-data-map/ocean-data`

## Backend Development Rules
- **Always use `uv` for virtual environment management**
- **Always use `uv pip` for package installations** (never use regular pip)
- **Always ensure the virtual environment is active when running Python 
- (use `uv run` or activate the venv in `backend/` folder)**
- **Never use conda** - only use uv for Python environment management
- **All test code must be in `backend/tests/` folder**
- Data downloads should be saved to `/Volumes/Backup/panta-rhei-data-map/ocean-data`
- **Credentials are stored in `backend/config/.env`**
  - Copernicus Marine Service: `CMEMS_USERNAME` and `CMEMS_PASSWORD`
  - NOAA API: `NOAA_API_KEY`

## Key Guidelines
- Follow existing code conventions and patterns
- Use the TodoWrite tool for planning multi-step tasks
- Run lint/typecheck commands after making changes
- Never commit changes unless explicitly requested
- **Always refer to `backend/docs/` for current project state and future tasks**
  - Check PRD file for project requirements and progress
  - Review existing documentation before starting work
- **Systematically test any new feature and review code for each code request**