"""Build processed model data for bayesian modeling"""

import logging

from tempoctrl.gradient_sports.modeldata import load_modeldata

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

def run_pipeline() -> None:
    load_modeldata()

def main():
    run_pipeline()

if __name__ == "__main__":
    main()

