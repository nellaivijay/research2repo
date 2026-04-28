"""Research2Repo Command Line Interface."""

import sys
from research2repo.version import __version__


def print_welcome():
    """Print welcome message with version information."""
    print("=" * 60)
    print(" 🎉 Welcome to Research2Repo")
    print(f" 🚀 Version: {__version__}")
    print(" 📚 Convert research papers to reproducible code repositories")
    print("=" * 60)


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print_welcome()
        print("\nUsage: research2repo <command> [options]")
        print("\nCommands:")
        print("  version     Show version information")
        print("  process     Process a research paper")
        print("  web         Start web interface")
        print("  evaluate    Evaluate generated code")
        print("\nUse 'research2repo <command> --help' for more information.")
        return
    
    command = sys.argv[1]
    
    if command == "version":
        print(f"Research2Repo version {__version__}")
    elif command == "process":
        print_welcome()
        print("\n📝 Processing papers...")
        print("This feature is under development.")
        print("For now, use the existing inference script:")
        print("  python test_code/inference.py <paper_path>")
    elif command == "web":
        print_welcome()
        print("\n🌐 Starting web interface...")
        print("This feature is under development.")
        print("For now, use the existing web app:")
        print("  python web/app.py")
    elif command == "evaluate":
        print_welcome()
        print("\n📊 Evaluating generated code...")
        print("This feature is under development.")
    else:
        print(f"Unknown command: {command}")
        print("Use 'research2repo --help' for available commands.")
        sys.exit(1)


if __name__ == "__main__":
    main()
