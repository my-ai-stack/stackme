"""
Stackme CLI — command-line interface for stackme.
"""
import argparse
import sys
import json
from . import Context


def main():
    parser = argparse.ArgumentParser(
        prog="stackme",
        description="🧠 Stackme — Your context brain for every AI.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # stackme add-fact "I run a fintech startup"
    p_add = sub.add_parser("add-fact", help="Add a fact to long-term memory")
    p_add.add_argument("content", help="Fact text")

    # stackme add "user message"
    p_add_msg = sub.add_parser("add", help="Add a user message (extracts facts)")
    p_add_msg.add_argument("content", help="Message text")

    # stackme get "what pricing?"
    p_get = sub.add_parser("get", help="Retrieve relevant context for a query")
    p_get.add_argument("query", help="Query string")
    p_get.add_argument("--top-k", type=int, default=5, help="Number of results")

    # stackme search "fintech"
    p_search = sub.add_parser("search", help="Search all memories")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--top-k", type=int, default=10, help="Number of results")

    # stackme facts
    p_facts = sub.add_parser("facts", help="List all stored facts")

    # stackme graph
    p_graph = sub.add_parser("graph", help="Query the knowledge graph")
    p_graph.add_argument("--subject", help="Filter by subject")

    # stackme history
    p_hist = sub.add_parser("history", help="Show session history")
    p_hist.add_argument("--last", type=int, help="Show last N turns")

    # stackme export
    p_export = sub.add_parser("export", help="Export all memory as JSON")

    # stackme count
    p_count = sub.add_parser("count", help="Count total memory items")

    # stackme clear-session
    p_clear = sub.add_parser("clear-session", help="Clear session memory only")

    # stackme clear-all
    p_clear_all = sub.add_parser("clear-all", help="Wipe ALL memory (irreversible)")

    args = parser.parse_args()
    ctx = Context()

    if args.command == "add-fact":
        id_ = ctx.add_fact(args.content)
        print(f"✅ Added fact: {id_}")

    elif args.command == "add":
        id_ = ctx.add_user_message(args.content)
        print(f"✅ Added message: {id_}")

    elif args.command == "get":
        result = ctx.get_relevant(args.query, top_k=args.top_k)
        if result:
            print(result)
        else:
            print("(no relevant context found)")

    elif args.command == "search":
        results = ctx.search(args.query, top_k=args.top_k)
        if results:
            for r in results:
                print(f"  • {r}")
        else:
            print("(no results)")

    elif args.command == "facts":
        facts = ctx.get_facts()
        if facts:
            for f in facts:
                print(f"  • {f}")
        else:
            print("(no facts stored yet)")

    elif args.command == "graph":
        facts = ctx.get_graph(subject=args.subject)
        if facts:
            for f in facts:
                print(f"  • {f.subject} — {f.predicate}: {f.value}")
        else:
            print("(no graph facts found)")

    elif args.command == "history":
        history = ctx.get_session_history(last_n=args.last)
        if history:
            for t in history:
                print(f"[{t['role']}]: {t['content']}")
        else:
            print("(no session history)")

    elif args.command == "export":
        print(json.dumps(ctx.export(), indent=2))

    elif args.command == "count":
        print(f"📊 {ctx.count()} memory items stored")

    elif args.command == "clear-session":
        ctx.clear_session()
        print("✅ Session cleared (long-term memory preserved)")

    elif args.command == "clear-all":
        confirm = input("⚠️  This will delete ALL memory. Are you sure? [y/N]: ")
        if confirm.lower() == "y":
            ctx.clear_all()
            print("✅ All memory wiped")
        else:
            print("Cancelled.")


if __name__ == "__main__":
    main()
