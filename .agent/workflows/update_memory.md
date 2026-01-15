---
description: Update the GEMINI.md memory file with new learnings from the session
---

1.  **Read the current Memory file**:
    Use `view_file` to read `/Users/lg/qi/code/AI-Gene-Detector/.agent/memory/GEMINI.md`.

2.  **Analyze the Session**:
    Reflect on the current session. Identify:
    -   New successful patterns or workflows.
    -   Corrections to existing rules.
    -   Specific constraints or preferences expressed by the user.

3.  **Append to Log**:
    Use `replace_file_content` or `multi_replace_file_content` to append a new entry to the `# 🧠 知识库更新日志` section at the end of the file.
    
    The entry format should be:
    ```markdown
    ## [YYYY-MM-DD] Session Summary
    - **Update Type**: (e.g., Rule Addition, Correction, New Tool Pattern)
    - **Details**: [Description of the change or learning]
    - **Reasoning**: [Why this update is necessary]
    ```

4.  **Confirm Update**:
    Inform the user that the memory has been updated and summarize the key additions.
