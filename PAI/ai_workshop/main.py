"""
╔══════════════════════════════════════════════════════════════════╗
║          FILE WORKSHOP AI  —  Multimodal Intelligence Layer      ║
║                                                                  ║
║  AI Features (Gemini):                                           ║
║    • Natural language commands  → file operations               ║
║    • Document Q&A  (chat with any file)                         ║
║    • Smart summarisation (PDF/DOCX/XLSX/PPTX)                   ║
║    • Image analysis & description                               ║
║    • Audio/Video transcription insight                          ║
║    • Auto-suggest conversion format                             ║
║    • Batch operation planning from plain English               ║
║                                                                  ║
║  Core (no AI needed):                                            ║
║    Convert · Split · Merge · Organise · Stamp                   ║
║    Protect · Compress · Metadata                                 ║
╚══════════════════════════════════════════════════════════════════╝
"""
from ui.app import AIWorkshopApp
def main():
    root = AIWorkshopApp()
    root.mainloop()
if __name__ == "__main__":
    main()
