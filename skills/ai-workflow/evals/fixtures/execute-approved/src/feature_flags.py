FLAGS = {"beta_search": False}


def enabled(name: str) -> bool:
    return FLAGS.get(name, False)
