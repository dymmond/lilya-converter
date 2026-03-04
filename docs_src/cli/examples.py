# Analyze
# lilya-converter analyze ./fastapi_project --json
# lilya-converter analyze ./django_project --source django --output ./reports/scan.json

# Convert with preview
# lilya-converter convert ./litestar_project ./lilya_project --source litestar --dry-run --diff

# Persist reports
# lilya-converter convert ./starlette_project ./lilya_project --source starlette --report ./reports/convert.json
# lilya-converter verify ./lilya_project --source django --report ./reports/verify.json

# Mapping introspection
# lilya-converter map rules --source flask
# lilya-converter map applied ./reports/convert.json
