import xml.etree.ElementTree as ET
import os
from pathlib import Path

def generate_interactive_html(eaf_file, wav_file, output_html, column_config):
    # 1. Parse the ELAN XML file
    try:
        tree = ET.parse(eaf_file)
        root = tree.getroot()
    except Exception as e:
        print(f"Error reading EAF file: {e}")
        return

    file_stem = Path(eaf_file).stem
    display_title = file_stem.replace('_', ' ')

    target_tiers = [tier for col in column_config for tier in col]

    # 2. Map Time Slots to Milliseconds
    time_slots = {}
    for ts in root.find('TIME_ORDER').findall('TIME_SLOT'):
        ts_id = ts.get('TIME_SLOT_ID')
        time_val = ts.get('TIME_VALUE')
        if time_val is not None:
            time_slots[ts_id] = int(time_val)

    # 3. Extract and Group Annotations by Timestamp
    segments = {}
    for tier in root.findall('TIER'):
        tier_id = tier.get('TIER_ID')
        if tier_id in target_tiers:
            for ann in tier.findall('ANNOTATION/ALIGNABLE_ANNOTATION'):
                ts1 = ann.get('TIME_SLOT_REF1')
                ts2 = ann.get('TIME_SLOT_REF2')
                value_elem = ann.find('ANNOTATION_VALUE')
                text_value = value_elem.text if value_elem is not None and value_elem.text else ""

                start_ms = time_slots.get(ts1, 0)
                end_ms = time_slots.get(ts2, 0)
                start_sec = start_ms / 1000.0
                end_sec = end_ms / 1000.0
                
                time_key = (start_sec, end_sec)
                if time_key not in segments:
                    segments[time_key] = {t: "" for t in target_tiers}
                segments[time_key][tier_id] = text_value

    sorted_segments = sorted(segments.items(), key=lambda x: x[0][0])
    if not sorted_segments:
        print("Warning: No annotations found for the specified tiers.")
        return

    # 4. Generate the HTML structure (Using Compact High-Density CSS)
    num_columns = len(column_config)
    
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>[TITLE]</title>
        <style>
            :root {
                /* DARK MODE (DEFAULT) */
                --bg-page: #222222;        
                --bg-surface: #2d2d2d;     
                --text-main: #eeeeee;      
                --text-muted: #a0a0a0;     
                --border-color: #404040;   
                --row-hover: #292929;      
                --accent-red: #d32f2f;     
                --accent-hover: #b71c1c;
                --highlight-bg: rgba(211, 47, 47, 0.15);
                --highlight-border: #ff5252;
                --input-bg: #222222;
            }

            @media (prefers-color-scheme: light) {
                 :root {
                    /* LIGHT MODE */
                    --bg-page: #f3f8f9;
                    --bg-surface: #ffffff;
                    --text-main: #111111;
                    --text-muted: #555555;
                    --border-color: #d1d9da;
                    --row-hover: #e9ecef;
                    --accent-red: #c62828; 
                    --accent-hover: #b71c1c;
                    --highlight-bg: #ffebeb;
                    --highlight-border: #d32f2f;
                    --input-bg: #ffffff;
                }
            }

            /* Compact Base Styles */
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 1400px; margin: 0 auto; padding: 0 1rem 1rem 1rem; background-color: var(--bg-page); color: var(--text-main); line-height: 1.3; font-size: 0.9rem; transition: background-color 0.3s, color 0.3s; }
            h1 { text-align: center; margin-top: 1rem; margin-bottom: 0.5rem; color: var(--text-main); text-transform: capitalize; font-size: 1.5rem; }
            
            /* Sticky Header */
            .sticky-header { position: sticky; top: 0; background: var(--bg-page); padding: 0.5rem 0; border-bottom: 2px solid var(--border-color); z-index: 100; }
            audio { width: 100%; height: 35px; border-radius: 4px; margin-bottom: 0.5rem; }
            
            /* Tighter Grid Setup */
            .grid-layout { display: flex; gap: 1rem; align-items: flex-start; }
            .left-spacer { flex-shrink: 0; width: 90px; } /* Slimmer Play button column */
            .content-grid { flex: 1; display: grid; grid-template-columns: repeat([NUM_COLUMNS], 1fr); gap: 1rem; }
            
            /* Compact Search Inputs */
            .search-container { margin-bottom: 0.5rem; }
            input.column-search { width: 100%; padding: 0.4rem 0.5rem; border: 1px solid var(--border-color); border-radius: 4px; background-color: var(--input-bg); color: var(--text-main); font-size: 0.85rem; box-sizing: border-box; transition: border-color 0.2s; }
            input.column-search:focus { outline: none; border-color: var(--accent-red); box-shadow: 0 0 0 2px var(--highlight-bg); }
            input.column-search::placeholder { color: var(--text-muted); }

            /* Dense Transcript Rows */
            .transcript-container { margin-top: 0.5rem; border: 1px solid var(--border-color); border-radius: 6px; background-color: var(--bg-surface); overflow: hidden; }
            .transcript-row { display: flex; align-items: flex-start; padding: 0.6rem 1rem; border-bottom: 1px solid var(--border-color); transition: background 0.2s ease; gap: 1rem; }
            .transcript-row:last-child { border-bottom: none; }
            .transcript-row:hover { background-color: var(--row-hover); }
            
            .row-controls { flex-shrink: 0; width: 90px; display: flex; flex-direction: column; gap: 0.3rem; align-items: stretch; }
            .play-btn { background: var(--accent-red); color: white; border: none; border-radius: 4px; padding: 0.3rem; cursor: pointer; font-weight: 600; font-size: 0.8rem; transition: background 0.2s; width: 100%; }
            .play-btn:hover { background: var(--accent-hover); }
            .time-label { font-size: 0.7rem; color: var(--text-muted); font-family: monospace; background: var(--bg-page); border: 1px solid var(--border-color); text-align: center; padding: 0.15rem; border-radius: 3px; }
            
            .transcript-column { display: flex; flex-direction: column; gap: 0.5rem; }
            .tier-block { display: flex; flex-direction: column; }
            .tier-name { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); font-weight: 700; margin-bottom: 0.1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.1rem; }
            .tier-text { font-size: 0.95rem; color: var(--text-main); }
            
            .highlight { background-color: var(--highlight-bg) !important; border-left: 4px solid var(--highlight-border); padding-left: calc(1rem - 4px); }
            
            @media (max-width: 768px) {
                .grid-layout { flex-direction: column; gap: 0.5rem; }
                .left-spacer { display: none; }
                .transcript-row { flex-direction: column; padding: 0.75rem; }
                .row-controls { width: 100%; flex-direction: row; align-items: center; justify-content: flex-start; gap: 0.5rem;}
                .play-btn { width: auto; padding: 0.4rem 1.5rem; }
                .content-grid { grid-template-columns: 1fr; gap: 0.75rem; }
            }
        </style>
    </head>
    <body>
        <h1>[TITLE]</h1>
        
        <div class="sticky-header">
            <audio id="main-audio" controls>
                <source src="[WAV_FILENAME]" type="audio/wav">
                Your browser does not support the audio element.
            </audio>
            
            <div class="search-container grid-layout">
                <div class="left-spacer"></div>
                <div class="content-grid">
                    [SEARCH_BARS]
                </div>
            </div>
        </div>

        <div class="transcript-container">
            [ROWS_HTML]
        </div>

        <script>
            const audio = document.getElementById('main-audio');
            let stopTime = null;

            // Audio Playback Logic
            function playSegment(start, end, rowId) {
                document.querySelectorAll('.transcript-row').forEach(row => row.classList.remove('highlight'));
                const activeRow = document.getElementById(rowId);
                if (activeRow) activeRow.classList.add('highlight');

                audio.currentTime = start;
                stopTime = end;
                audio.play();
            }

            audio.addEventListener('timeupdate', () => {
                if (stopTime && audio.currentTime >= stopTime) {
                    audio.pause();
                    stopTime = null;
                }
            });

            // Live Search Logic
            const searchInputs = document.querySelectorAll('.column-search');
            const rows = document.querySelectorAll('.transcript-row');

            searchInputs.forEach(input => {
                input.addEventListener('input', () => {
                    // Get current search query for each column
                    const queries = Array.from(searchInputs).map(i => i.value.toLowerCase().trim());
                    
                    rows.forEach(row => {
                        const columns = row.querySelectorAll('.transcript-column');
                        let isMatch = true;
                        
                        queries.forEach((query, index) => {
                            if (query && columns[index]) {
                                const text = columns[index].textContent.toLowerCase();
                                if (!text.includes(query)) {
                                    isMatch = false;
                                }
                            }
                        });
                        
                        // Show row if it matches all active filters, otherwise hide it
                        row.style.display = isMatch ? 'flex' : 'none';
                    });
                });
            });
        </script>
    </body>
    </html>
    """

    # 5. Generate Search Bars
    search_bars_html = ""
    for i, column in enumerate(column_config):
        # Use the first tier's name as the placeholder text for the column's search bar
        placeholder_name = column[0].replace('_', ' ')
        search_bars_html += f'<input type="text" class="column-search" placeholder="Search {placeholder_name}..." aria-label="Search column {i+1}">'

    # 6. Populate the rows
    rows_html = ""
    for i, ((start_sec, end_sec), tier_data) in enumerate(sorted_segments):
        row_id = f"row_{i}"
        
        columns_html = ""
        for column in column_config:
            column_content = ""
            for tier_name in column:
                text = tier_data.get(tier_name, "")
                display_name = tier_name.replace('_', ' ')
                
                column_content += f"""
                <div class="tier-block">
                    <div class="tier-name">{display_name}</div>
                    <div class="tier-text">{text if text else "<em>(blank)</em>"}</div>
                </div>
                """
            columns_html += f'<div class="transcript-column">{column_content}</div>'

        rows_html += f"""
        <div class="transcript-row" id="{row_id}">
            <div class="row-controls">
                <button class="play-btn" onclick="playSegment({start_sec}, {end_sec}, '{row_id}')">▶ Play</button>
                <div class="time-label">{start_sec:.2f}s - {end_sec:.2f}s</div>
            </div>
            <div class="content-grid">
                {columns_html}
            </div>
        </div>
        """

    # 7. Finalize and save using safe replacements
    final_html = html_template.replace('[TITLE]', display_title)
    final_html = final_html.replace('[NUM_COLUMNS]', str(num_columns))
    final_html = final_html.replace('[WAV_FILENAME]', os.path.basename(wav_file))
    final_html = final_html.replace('[SEARCH_BARS]', search_bars_html)
    final_html = final_html.replace('[ROWS_HTML]', rows_html)

    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"Success! Generated compact HTML at {output_html}")

if __name__ == '__main__':
    # Your file paths
    EAF_FILENAME = Path(r"C:/Users/finna/OneDrive - Yale University/Documents/Domari/Experimental script/abu hasan.eaf")
    WAV_FILENAME = Path(r"C:/Users/finna/OneDrive - Yale University/Documents/Domari/Experimental script/abu hasan.wav")
    OUTPUT_FILENAME = Path(r"C:/Users/finna/OneDrive - Yale University/Documents/Domari/Experimental script/index.html")
    
    # Column configuration
    COLUMN_CONFIG = [
        ["Matras_Jerusalem_Domari_2000"],
        ["Macalister_Domari_1914"],
        ["English"]
    ]

    if os.path.exists(EAF_FILENAME):
        generate_interactive_html(EAF_FILENAME, WAV_FILENAME, OUTPUT_FILENAME, COLUMN_CONFIG)
    else:
        print(f"Could not find {EAF_FILENAME}. Please ensure the file paths match.")