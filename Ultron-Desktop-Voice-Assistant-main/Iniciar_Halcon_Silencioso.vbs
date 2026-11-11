' ==============================================================================
' HALCÓN AI Assistant - Lanzador Silencioso en Segundo Plano
' Ejecuta HALCÓN sin mostrar ninguna ventana negra de terminal (CMD)
' ==============================================================================
Option Explicit

Dim fso, wshShell, scriptDir, batFile

Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

Set wshShell = CreateObject("WScript.Shell")
wshShell.CurrentDirectory = scriptDir

batFile = scriptDir & "\Iniciar_Halcon.bat"

' Ejecutar Iniciar_Halcon.bat con ventana oculta (0 = SW_HIDE, False = asincrono en background)
On Error Resume Next
wshShell.Run "cmd.exe /c """ & batFile & """", 0, False

If Err.Number <> 0 Then
    ' Fallback ejecutando directamente python en modo oculto
    Err.Clear
    wshShell.Run "python main.py --hud", 0, False
End If
