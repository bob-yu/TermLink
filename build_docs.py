from utils.docs_builder import build_documentation


if __name__ == "__main__":
    index = build_documentation()
    print(f"Generated documentation: {index}")
