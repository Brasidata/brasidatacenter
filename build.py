import pathlib
import html
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, FOAF, SKOS

def get_local_name(uri: URIRef) -> str:
    """Extracts the local name from a URI."""
    uri_str = str(uri)
    if "#" in uri_str:
        return uri_str.split("#")[-1]
    return uri_str.split("/")[-1]

def format_value(value) -> str:
    """Formats an RDF value for HTML output."""
    if isinstance(value, URIRef):
        uri_str = str(value)
        local_name = get_local_name(value)
        
        # If it's an internal link (our own namespace)
        if "kb.elias.eng.br/nid.ttl#" in uri_str:
            return f'<a href="#{local_name}">{html.escape(local_name)}</a>'
        # If it's an external link (like github, elias.eng.br, etc)
        elif uri_str.startswith("http"):
            return f'<a href="{html.escape(uri_str)}">{html.escape(uri_str)}</a>'
        
        return html.escape(local_name)
    else:
        return html.escape(str(value))

def generate_html(graph: Graph, base_uri: str) -> str:
    entities_html = []
    
    # Get all distinct subjects
    subjects = set(graph.subjects(None, None))
    
    # Filter out blank nodes and ontology definition itself
    filtered_subjects = []
    for s in subjects:
        if not isinstance(s, URIRef):
            continue
        if str(s) == base_uri.rstrip("#"):
            continue
            
        # Check if it's an AnnotationProperty or Class
        types = list(graph.objects(s, RDF.type))
        if URIRef("http://www.w3.org/2002/07/owl#AnnotationProperty") in types:
            continue
            
        # Ignore owl:Class UNLESS it belongs to our own namespace (base_uri)
        if URIRef("http://www.w3.org/2002/07/owl#Class") in types:
            if not str(s).startswith(base_uri):
                continue
                
        filtered_subjects.append(s)
        
    subjects = filtered_subjects
    
    # Sort subjects by local name
    subjects.sort(key=lambda s: get_local_name(s))

    for subject in subjects:
        local_id = get_local_name(subject)
        subject_str = str(subject)
        
        # Determine title (try foaf:name, schema:name, or fallback to local ID)
        title = local_id
        for name_prop in [FOAF.name, URIRef("https://schema.org/name")]:
            name_val = graph.value(subject, name_prop)
            if name_val:
                title = str(name_val)
                break

        # Group properties
        properties = {}
        for p, o in graph.predicate_objects(subject):
            p_name = get_local_name(p)
            # Use prefixed names for common properties for better readability
            if p == RDF.type:
                p_name = "Type (rdf:type)"
            elif str(p).startswith(str(FOAF)):
                p_name = f"foaf:{get_local_name(p)}"
            elif str(p).startswith("https://schema.org/"):
                p_name = f"schema:{get_local_name(p)}"
            elif str(p).startswith("http://www.w3.org/ns/org#"):
                p_name = f"org:{get_local_name(p)}"
                
            if p_name not in properties:
                properties[p_name] = []
            properties[p_name].append(o)

        # Build table rows
        rows_html = ""
        for p_name, values in sorted(properties.items()):
            # Format values with language tags
            formatted_values_list = []
            for v in values:
                lang = getattr(v, "language", None)
                formatted_v = format_value(v)
                if lang:
                    formatted_values_list.append(f'<span class="lang-value" data-lang="{html.escape(lang)}">{formatted_v}</span>')
                else:
                    formatted_values_list.append(f'<span class="lang-value" data-lang="any">{formatted_v}</span>')
            
            formatted_values = ", ".join(formatted_values_list)
            rows_html += f"<tr><th>{html.escape(p_name)}</th><td>{formatted_values}</td></tr>\n"

        # Build entity block
        entity_html = f"""
        <div class="entity" id="{html.escape(local_id)}">
            <h3 class="entity-title">{html.escape(title)}</h3>
            <span class="uri">{html.escape(subject_str)}</span>
            <table class="props">
                {rows_html}
            </table>
        </div>"""
        entities_html.append(entity_html)

    # HTML Template
    template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Base Namespace (NID) - KB Elias</title>
    <style>
        :root {{
            --text: #333;
            --muted: #666;
            --rule: #eaeaea;
            --accent: #1f4f9a;
            --bg: #fdfdfd;
        }}
        body {{
            margin: 0;
            background: var(--bg);
            color: var(--text);
            font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
            line-height: 1.6;
        }}
        .container {{
            max-width: 800px;
            margin: 40px auto;
            padding: 0 20px;
        }}
        header {{
            border-bottom: 2px solid var(--rule);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        h1 {{
            margin: 0 0 10px 0;
            color: var(--accent);
        }}
        h2 {{
            border-bottom: 1px solid var(--rule);
            padding-bottom: 5px;
            margin-top: 40px;
        }}
        code {{
            background: #f1f1f1;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9em;
            color: #d63384;
        }}
        .entity {{
            background: white;
            border: 1px solid var(--rule);
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }}
        .entity-title {{
            margin-top: 0;
            color: var(--accent);
        }}
        .uri {{
            font-family: monospace;
            color: var(--muted);
            margin-bottom: 15px;
            display: block;
            word-break: break-all;
        }}
        .props {{
            width: 100%;
            border-collapse: collapse;
        }}
        .props th, .props td {{
            text-align: left;
            padding: 8px 12px;
            border-bottom: 1px solid var(--rule);
        }}
        .props th {{
            width: 30%;
            color: var(--muted);
            font-weight: normal;
        }}
        .rdf-link {{
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background: var(--accent);
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-weight: bold;
        }}
        .rdf-link:hover {{
            background: #153b75;
        }}
        
        /* i18n styles */
        .lang-value {{ display: inline; }}
        .lang-value.hidden {{ display: none !important; }}
        
        .header-controls {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        .lang-selector {{
            margin-top: 20px;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--rule);
            background: white;
            font-size: 14px;
            cursor: pointer;
        }}
    </style>
</head>
<body>

<div class="container">
    <header>
        <div class="header-controls">
            <div>
                <h1>Base Namespace (NID)</h1>
                <p>Vocabulary and resource identifiers for Elias Magalhães's knowledge base.</p>
                <p><strong>Base URI:</strong> <code>{html.escape(base_uri)}</code></p>
                <a href="/nid.ttl" class="rdf-link">⬇ Download RDF data (Turtle)</a>
            </div>
            <select id="lang-select" class="lang-selector">
                <option value="en">�� English (en)</option>
                <option value="pt-br">�� Portuguese (pt-BR)</option>
            </select>
        </div>
    </header>

    <section>
        <h2>Named Individuals</h2>
        {"".join(entities_html)}
    </section>
</div>

<script>
    document.addEventListener('DOMContentLoaded', () => {{
        const select = document.getElementById('lang-select');
        
        // Function to update visibility of values based on selected language
        function updateLanguage(targetLang) {{
            const values = document.querySelectorAll('.lang-value');
            
            // First, process all items to handle multi-language properties
            // We group them by their parent <td> to ensure we don't hide everything
            // if a property doesn't have a translation in the target language.
            
            const cells = document.querySelectorAll('.props td');
            
            cells.forEach(td => {{
                const items = Array.from(td.querySelectorAll('.lang-value'));
                if (items.length === 0) return; // Skip if no language tags
                
                // Find items that match the target language
                const hasTargetLang = items.some(item => item.dataset.lang === targetLang);
                
                items.forEach((item, index) => {{
                    const lang = item.dataset.lang;
                    
                    // Always show items without specific language ("any")
                    if (lang === 'any') {{
                        item.classList.remove('hidden');
                        
                        // Clean up commas for "any" items
                        const nextNode = item.nextSibling;
                        if (nextNode && nextNode.nodeType === Node.TEXT_NODE) {{
                            nextNode.textContent = (index < items.length - 1) ? ", " : "";
                        }}
                    }} 
                    // If we have the target language, only show that one
                    else if (hasTargetLang) {{
                        if (lang === targetLang) {{
                            item.classList.remove('hidden');
                        }} else {{
                            item.classList.add('hidden');
                        }}
                    }} 
                    // Fallback: If we don't have the target lang, show English or the first available
                    else {{
                        const fallbackLang = items.some(i => i.dataset.lang === 'en') ? 'en' : items[0].dataset.lang;
                        if (lang === fallbackLang) {{
                            item.classList.remove('hidden');
                        }} else {{
                            item.classList.add('hidden');
                        }}
                    }}
                }});
                
                // Clean up trailing commas in the cell after hiding elements
                cleanUpCommas(td);
            }});
        }}
        
        function cleanUpCommas(container) {{
            const visibleItems = Array.from(container.querySelectorAll('.lang-value:not(.hidden)'));
            
            visibleItems.forEach((item, index) => {{
                // Find the next text node (which contains the comma)
                let nextNode = item.nextSibling;
                
                // If there's a text node after this item
                if (nextNode && nextNode.nodeType === Node.TEXT_NODE) {{
                    // If it's the last visible item, remove the comma
                    if (index === visibleItems.length - 1) {{
                        nextNode.textContent = "";
                    }} 
                    // Otherwise, ensure there is a comma
                    else {{
                        nextNode.textContent = ", ";
                    }}
                }}
            }});
        }}

        // Listen for manual changes
        select.addEventListener('change', (e) => {{
            updateLanguage(e.target.value);
            // Save preference
            try {{ localStorage.setItem('preferred-lang', e.target.value); }} catch(e) {{}}
        }});

        // Determine initial language
        let initialLang = 'en';
        try {{
            const saved = localStorage.getItem('preferred-lang');
            if (saved) {{
                initialLang = saved;
            }} else {{
                // Try to get from browser
                const browserLang = navigator.language.toLowerCase();
                if (browserLang.startsWith('pt')) initialLang = 'pt-br';
            }}
        }} catch(e) {{}}
        
        // Set dropdown and trigger update
        select.value = initialLang;
        updateLanguage(initialLang);
    }});
</script>
</body>
</html>"""
    
    return template

def main():
    base_dir = pathlib.Path(__file__).resolve().parent
    ttl_path = base_dir / "nid.ttl"
    html_path = base_dir / "nid" / "index.html"
    
    # Define Base URI matching the ontology
    base_uri = "http://kb.elias.eng.br/nid/elias.ttl#"

    print(f"Loading RDF from {ttl_path}...")
    g = Graph()
    g.parse(ttl_path, format="ttl")
    
    print(f"Generating HTML documentation...")
    html_content = generate_html(g, base_uri)
    
    # Ensure directory exists
    html_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Writing to {html_path}...")
    html_path.write_text(html_content, encoding="utf-8")

if __name__ == "__main__":
    main()
