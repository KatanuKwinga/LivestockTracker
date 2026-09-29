"""Load synthetic practice data into the real database.

Run from the project root (venv active):

    python -m ml.seed --farmer-email you@example.com            # add 300 animals
    python -m ml.seed --farmer-email you@example.com --animals 100
    python -m ml.seed --farmer-email you@example.com --remove   # delete them again

The farmer account must already exist (register it in the app first).
Tip: use a separate demo farmer account rather than your real one, so
practice data never mixes with real records.

The data ends at today's date. If you demo weeks later, re-run with
--remove then seed again so the "recent weight" signals are fresh.
"""

import argparse
import sys

from app import create_app
from app.models import User
from ml.data import remove_synthetic, seed_synthetic
from ml.synthetic import generate_synthetic_data


def main():
    parser = argparse.ArgumentParser(description="Seed or remove synthetic livestock data.")
    parser.add_argument("--farmer-email", required=True)
    parser.add_argument("--animals", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42, help="Random seed (same seed = same data).")
    parser.add_argument("--remove", action="store_true", help="Delete this farmer's synthetic animals.")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=args.farmer_email.lower().strip()).first()
        if user is None or user.farmer is None:
            sys.exit(f"No farmer account with email {args.farmer_email}. Register one in the app first.")
        farmer_id = user.farmer.farmer_id

        if args.remove:
            n = remove_synthetic(farmer_id)
            print(f"Removed {n} synthetic animals (and their records).")
            return

        print(f"Generating {args.animals} animals with a year of history...")
        frames = generate_synthetic_data(n_animals=args.animals, seed=args.seed)
        print(f"Inserting {len(frames['weights'])} weigh-ins and {len(frames['health'])} health records "
              "(can take a minute against a cloud database)...")
        n = seed_synthetic(frames, farmer_id)
        print(f"Done: {n} animals added to {args.farmer_email}. Next: python -m ml.train")


if __name__ == "__main__":
    main()
