"""
Stackme Demo — Gradio interface for HuggingFace Spaces.
This lets users try Stackme directly in the browser.
"""
import gradio as gr
from stackme import Context

ctx = Context()


def add_fact(fact: str):
    if not fact.strip():
        return "⚠️ Please enter a fact.", get_stats()
    id_ = ctx.add_fact(fact)
    return f"✅ Saved: {id_}", get_stats()


def add_message(msg: str):
    if not msg.strip():
        return "⚠️ Please enter a message.", get_stats()
    id_ = ctx.add_user_message(msg)
    return f"✅ Message added + facts auto-extracted: {id_}", get_stats()


def get_context(query: str, top_k: int = 5):
    if not query.strip():
        return "⚠️ Enter a query."
    result = ctx.get_relevant(query, top_k=top_k)
    return result if result else "(no relevant context found)"


def get_all_facts():
    facts = ctx.get_facts()
    if not facts:
        return "(no facts yet — add some above!)"
    return "\n".join(f"• {f}" for f in facts)


def get_graph(subject: str = ""):
    facts = ctx.get_graph(subject=subject.strip() or None)
    if not facts:
        return "(no graph facts yet)"
    return "\n".join(f"• {f.subject} — {f.predicate}: {f.value}" for f in facts)


def get_history():
    history = ctx.get_session_history()
    if not history:
        return "(no session history)"
    return "\n".join(f"[{t['role']}]: {t['content']}" for t in history)


def get_stats():
    return f"📊 {ctx.count()} total items stored"


with gr.Blocks(title="🧠 Stackme — Context Brain") as demo:
    gr.Markdown("# 🧠 Stackme — Your Context Brain\n*100% local memory for any AI. No server. No account.*")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### ➕ Add Memory")
            fact_input = gr.Textbox(label="Add a Fact", placeholder="I run a fintech B2B SaaS...")
            fact_btn = gr.Button("Save Fact", variant="primary")
            msg_input = gr.Textbox(label="Add User Message (auto-extracts facts)", placeholder="I'm building a B2B SaaS targeting fintech...")
            msg_btn = gr.Button("Add Message", variant="secondary")
            status = gr.Textbox(label="Status", interactive=False)

        with gr.Column(scale=1):
            gr.Markdown("### 🔍 Get Context")
            query_input = gr.Textbox(label="Query", placeholder="What pricing should we use?")
            top_k = gr.Slider(1, 10, value=5, step=1, label="Top K results")
            get_btn = gr.Button("Retrieve Context", variant="primary")
            context_output = gr.Textbox(label="Retrieved Context", lines=8, interactive=False)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📚 All Facts")
            facts_output = gr.Textbox(label="Facts", lines=6, interactive=False)
            refresh_facts = gr.Button("🔄 Refresh Facts")

        with gr.Column(scale=1):
            gr.Markdown("### 🔗 Knowledge Graph")
            graph_subject = gr.Textbox(label="Filter by Subject (optional)", placeholder="User")
            graph_output = gr.Textbox(label="Graph Facts", lines=6, interactive=False)
            refresh_graph = gr.Button("🔄 Refresh Graph")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 💬 Session History")
            history_output = gr.Textbox(label="Session", lines=6, interactive=False)
            refresh_history = gr.Button("🔄 Refresh History")

        with gr.Column(scale=1):
            gr.Markdown("### 📊 Stats")
            stats_output = gr.Textbox(label="Memory Stats", interactive=False)
            refresh_stats = gr.Button("🔄 Refresh Stats")
            clear_session = gr.Button("🗑️ Clear Session", variant="stop")
            clear_all = gr.Button("💣 Clear ALL Memory", variant="stop", visible=False)  # hidden by default for safety

    # Wire up
    fact_btn.click(add_fact, [fact_input], [status, stats_output])
    msg_btn.click(add_message, [msg_input], [status, stats_output])
    get_btn.click(get_context, [query_input, top_k], context_output)
    refresh_facts.click(get_all_facts, outputs=facts_output)
    refresh_graph.click(get_graph, [graph_subject], graph_output)
    refresh_history.click(get_history, outputs=history_output)
    refresh_stats.click(get_stats, outputs=stats_output)
    clear_session.click(fn=lambda: (ctx.clear_session(), "✅ Session cleared"), outputs=status)

    # Load initial state
    demo.load(fn=get_stats, outputs=stats_output)

if __name__ == "__main__":
    demo.launch()
