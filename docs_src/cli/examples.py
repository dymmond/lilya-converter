# Analyze
# lilya-converter analyze ./fastapi_project --json

# Convert with preview
# lilya-converter convert ./fastapi_project ./lilya_project --dry-run --diff

# Persist reports
# lilya-converter convert ./fastapi_project ./lilya_project --report ./reports/convert.json
# lilya-converter verify ./lilya_project --report ./reports/verify.json

# Mapping introspection
# lilya-converter map rules
# lilya-converter map applied ./reports/convert.json
