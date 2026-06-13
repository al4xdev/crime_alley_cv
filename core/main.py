from .core import Core

def main():
    Core.setup()\
        .setup_paths()\
        .fetch_github_username()\
        .fetch_user_repositories()\
        .clone_repositories()

if __name__ == "__main__":
    main()
