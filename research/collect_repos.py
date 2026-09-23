#!/usr/bin/env python3
"""Read-only public GitHub research collector. Never executes repository code."""
import concurrent.futures, datetime, hashlib, json, pathlib, re, subprocess, tarfile, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
REPOS = {
 'codex':'openai/codex', 'claude-code':'anthropics/claude-code',
 'opencode':'anomalyco/opencode', 'pi':'earendil-works/pi',
 'hermes':'NousResearch/hermes-agent', 'gemini-cli':'google-gemini/gemini-cli',
 'qwen-code':'QwenLM/qwen-code', 'kimi-code':'MoonshotAI/kimi-code',
 'mimo-code':'XiaomiMiMo/MiMo-Code', 'deepseek-harness':'deepseek-ai/deepseek-harness',
 'cline':'cline/cline', 'kilo':'Kilo-Org/kilocode', 'continue':'continuedev/continue',
 'aider':'Aider-AI/aider', 'goose':'block/goose', 'crush':'charmbracelet/crush',
 'vibe':'mistralai/mistral-vibe', 'openhands':'OpenHands/OpenHands',
 'openclaw':'openclaw/openclaw', 'chatbox':'chatboxai/chatbox',
 'cherry-studio':'CherryHQ/cherry-studio', 'open-webui':'open-webui/open-webui',
 'librechat':'danny-avila/LibreChat', 'lobehub':'lobehub/lobehub',
 'anythingllm':'Mintplex-Labs/anything-llm', 'zed':'zed-industries/zed',
 'copilot':'microsoft/vscode-copilot-chat', 'roo-code':'RooCodeInc/Roo-Code',
 'dify':'langgenius/dify', 'n8n':'n8n-io/n8n',
 'swe-agent':'SWE-agent/SWE-agent', 'mini-swe-agent':'SWE-agent/mini-swe-agent',
 'agent-zero':'agent0ai/agent-zero', 'trae-agent':'bytedance/trae-agent',
 'oh-my-openagent':'code-yeongyu/oh-my-openagent',
 'vscode':'microsoft/vscode', 'openhands-sdk':'OpenHands/software-agent-sdk',
 'qwen-docs':'QwenLM/qwen-code-docs',
 'grok-build':'xai-org/grok-build',
 'avante':'yetone/avante.nvim', 'codecompanion':'olimorris/codecompanion.nvim',
}
HEADERS={'User-Agent':'harness-comparison-research/1.0','Accept':'application/vnd.github+json'}

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=90)

def collect(item):
    name, repo = item
    dest = ROOT/'repos'/name
    dest.mkdir(parents=True, exist_ok=True)
    try:
        if (dest/'manifest.json').exists():
            return {'name':name,'status':'cached'}
        meta=json.load(get('https://api.github.com/repos/'+repo))
        (dest/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
        repo=meta['full_name']
        sha=subprocess.check_output(['git','ls-remote','https://github.com/'+repo+'.git','HEAD'],text=True,timeout=60).split()[0]
        manifest={'repo':repo,'sha':sha,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[]}
        inventory=[]
        url=f'https://codeload.github.com/{repo}/tar.gz/{sha}'
        with get(url) as response, tarfile.open(fileobj=response,mode='r|gz') as tf:
            for member in tf:
                if not member.isfile(): continue
                rel='/'.join(member.name.split('/')[1:])
                if not rel or '..' in pathlib.PurePosixPath(rel).parts: continue
                inventory.append({'path':rel,'size':member.size})
                suffix=pathlib.PurePosixPath(rel).suffix.lower()
                skip=re.search(r'(^|/)(node_modules|vendor|third_party|fixtures|__snapshots__|\.git|translations|locales)/',rel)
                is_doc=suffix in ('.md','.mdx','.rst')
                is_source=suffix in ('.py','.ts','.tsx','.rs','.go','.js','.svelte','.json','.toml','.yaml','.yml','.lua')
                selected=is_doc or (is_source and re.search(r'(agent|session|context|compact|loop|provider|model|permission|sandbox|memory|tool|runtime|checkpoint|coder|extension|workflow|orchestrat|config)',rel,re.I))
                if skip or not selected or member.size>700000 or (not is_doc and re.search(r'(test|spec|lock|snapshot)',rel,re.I)): continue
                data=tf.extractfile(member).read()
                out=dest/'files'/rel
                out.parent.mkdir(parents=True,exist_ok=True)
                out.write_bytes(data)
                manifest['files'].append({'path':rel,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'kind':'doc' if is_doc else 'source'})
        (dest/'tree.json').write_text(json.dumps(inventory,ensure_ascii=False))
        (dest/'tree.txt').write_text('\n'.join(x['path'] for x in inventory))
        (dest/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
        return {'name':name,'repo':repo,'sha':sha,'stars':meta['stargazers_count'],'pushed_at':meta['pushed_at'],'archived':meta['archived'],'tree_files':len(inventory),'saved_files':len(manifest['files'])}
    except Exception as e:
        (dest/'error.txt').write_text(str(e))
        return {'name':name,'error':str(e)}

if __name__=='__main__':
    import sys
    names=sys.argv[1:]
    chosen={k:v for k,v in REPOS.items() if not names or k in names}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for result in pool.map(collect, chosen.items()): print(json.dumps(result,ensure_ascii=False),flush=True)
