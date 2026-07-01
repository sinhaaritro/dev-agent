import sys
import re
import os
import argparse

def extract_headers(filepath):
    """Extract all h2 and h3 headers from a markdown file."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"ERROR: Reading file {filepath} failed: {e}")
        return None
    
    # Extract headers starting with ## or ###
    headers = re.findall(r'^#{2,3}\s+(.+)$', content, re.MULTILINE)
    return [h.strip() for h in headers]

def verify_markdown_file(filepath, template_headers):
    """Verify that a given markdown file has headers matching all template headers."""
    target_headers = extract_headers(filepath)
    if target_headers is None:
        return False

    missing = []
    for t_header in template_headers:
        # Search for template header in target headers (case-insensitive substring match)
        pattern = re.compile(re.escape(t_header), re.IGNORECASE)
        found = False
        for r_header in target_headers:
            if pattern.search(r_header):
                found = True
                break
        if not found:
            missing.append(t_header)
            
    if missing:
        print(f"[FAIL] '{filepath}' is missing required sections from template:")
        for m in missing:
            print(f"   - {m}")
        return False
    else:
        print(f"[PASS] '{filepath}' contains all required sections from template.")
        return True

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    parser = argparse.ArgumentParser(description="Verify markdown file sections against a template.")
    parser.add_argument('--template', required=True, help="Path to the template markdown file")
    parser.add_argument('files', nargs='+', help="Paths to the markdown files to verify")
    
    args = parser.parse_args()
    
    template_headers = extract_headers(args.template)
    if not template_headers:
        print(f"ERROR: Could not extract headers from template file '{args.template}'")
        sys.exit(1)
        
    success = True
    for path in args.files:
        if not verify_markdown_file(path, template_headers):
            success = False
            
    if not success:
        sys.exit(1)
