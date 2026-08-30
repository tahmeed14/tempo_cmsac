from tempoctrl.gradient_sports.join import possession_load
overwrite = True

def main() -> None:
    """Build integrated possession files for configured matches."""
    for match_id in range(10514, 10518):
        possession_load(match_id, overwrite=overwrite)


if __name__ == "__main__":
    main()
