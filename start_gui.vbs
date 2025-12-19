' Auto Simulated Universe - GUI 启动器 (隐藏窗口)
' 双击此文件启动 GUI 配置面板

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 获取脚本所在目录
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' 使用 pythonw 运行(无控制台窗口)
pythonwPath = "pythonw"
serverScript = scriptDir & "\gui_server.py"

' 尝试运行
On Error Resume Next
WshShell.Run """" & pythonwPath & """ """ & serverScript & """", 0, False

If Err.Number <> 0 Then
    ' 如果 pythonw 失败,尝试使用 python
    WshShell.Run "python """ & serverScript & """", 0, False
End If
