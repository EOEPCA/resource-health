.DEFAULT_GOAL := web-service/page/schema.d.ts

api-service-fastapi/.venv/created_by_make: api-service-fastapi/requirements.txt
	cd api-service-fastapi; \
	rm -Rf .venv; \
	( \
	python -m venv .venv; \
        . .venv/bin/activate; \
	pip install -r requirements.txt; \
        ); \
	touch .venv/created_by_make; \
	cd $(CURDIR)

api-service-fastapi/openapi.json: api-service-fastapi/.venv/created_by_make api-service-fastapi/generate-openapi.py api-service-fastapi/main.py
	cd api-service-fastapi; \
	( \
	. .venv/bin/activate; \
	python generate-openapi.py > openapi.json.out || rm openapi.json.bak; \
	); \
	mv openapi.json.out openapi.json; \
	cd $(CURDIR)

web-service/page/schema.d.ts: api-service-fastapi/openapi.json
	cd web-service/page; \
	npx openapi-typescript ../../api-service-fastapi/openapi.json -o schema.d.ts; \
	cd $(CURDIR)
