# Lambda rejects an OCI manifest, so this must be built with buildx and
#   --provenance=false --sbom=false
# and the base architecture must match the function's, or `import cv2` dies
# on an illegal instruction rather than an import error.
FROM public.ecr.aws/lambda/python:3.12

# opencv-python-headless still dlopen's these at import
RUN dnf install -y mesa-libGL glib2 && dnf clean all

# pinned: the competition requires OpenCV 5 substantively, and an unpinned
# install is free to resolve elsewhere later. 5.0.0.93 is the first 5.x on
# PyPI (checked 2026-09-20).
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir "opencv-python-headless==5.0.0.93" "numpy>=2.0"

COPY src/ ${LAMBDA_TASK_ROOT}/src/
COPY aws/handler.py ${LAMBDA_TASK_ROOT}/

CMD [ "handler.handler" ]
