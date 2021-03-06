import sys
import os

from System.Diagnostics import Process, ProcessStartInfo

import clr
clr.AddReference('Microsoft.TeamFoundation.VersionControl.Client')
clr.AddReference('Microsoft.TeamFoundation.Client')
clr.AddReference('Microsoft.TeamFoundation.VersionControl.Common')
from Microsoft.TeamFoundation.VersionControl.Client import *
from Microsoft.TeamFoundation.Client import *
from Microsoft.TeamFoundation.VersionControl.Common import *

tfs = TeamFoundationServer('http://tcvstf:8080/tfs/tc')
tfs.Authenticate()

vcs = tfs.GetService(VersionControlServer)
assert isinstance(vcs, VersionControlServer)

mc = vcs.GetMergeCandidates('$/TCWCS/Python/Main/Open_Source/Incubation/Django/Release', '$/TCWCS/Python/Main/Open_Source/Release', RecursionType.Full)
hg_root = r'C:\Source\hgtest\pytools'
workspace_root = r'F:\Product\TCP0\Open_Source'
ws = vcs.TryGetWorkspace(workspace_root)

merge_from = ItemSpec('$/TCWCS/Python/Main/Open_Source/Incubation/Django/Release', RecursionType.Full)
merge_to = '$/TCWCS/Python/Main/Open_Source/Release'
cur_version = 28501

path = os.path.join(os.environ['WinDir'], r'System32\WindowsPowerShell\v1.0\powershell.exe')


for x in reversed(list(vcs.QueryHistory('$/TCWCS/Python/Main/Open_Source/Incubation/Django/Release', VersionSpec.Latest, 0, RecursionType.Full, None, None, None, int.MaxValue, False, False))): 
    if cur_version >= x.ChangesetId:
        continue

    assert isinstance(x, Changeset)
    print '####################################################################################'
    print 'CHeckin: ' + str(x.ChangesetId)
    status = ws.Merge(
             merge_from, 
             merge_to, 
             VersionSpec.Parse('C' + str(cur_version), None)[0], 
             VersionSpec.Parse('C' + str(x.ChangesetId), None)[0], 
             LockLevel.None, 
             MergeOptionsEx.None)

    if status.GetFailures():
        print 'failed'
        print status.GetFailures()
        sys.exit(1)
    
    if status.NoActionNeeded:
        print 'No action needed', x.ChangesetId
        cur_version = x.ChangesetId
        continue
    print 'Warnings', status.HaveResolvableWarnings
    print 'Conflicts', status.NumConflicts
    for conflict in ws.QueryConflicts(('$/TCWCS/Python/Main/Open_Source/', ), True):
        assert isinstance(conflict, Conflict)
        print 'Can Merge', conflict.CanMergeContent
        conflict.Resolution = Resolution.AcceptMerge
        conflict.ResolutionOptions.UseInternalEngine = True
        ws.ResolveConflict(conflict)
        if not conflict.IsResolved:
            if conflict.CanMergeContent:
                conflict.Resolution = Resolution.AcceptYours
                ws.ResolveConflict(conflict)
                if not conflict.IsResolved:
                    print 'Failed to resolve conflict', dir(conflict)
                    sys.exit(1)
            else:
                print 'Failed to resolve conflict', dir(conflict)
                sys.exit(1)

    ws.CheckIn(ws.GetPendingChanges(), x.Comment)    
    comment = x.Comment.Replace("'", "''").Replace(unichr(8217), "''")
    psi = ProcessStartInfo(path, 
                           r'"' + workspace_root + "\Tools\CodePlex\Sync.ps1\" push '" + 
                           hg_root + "' '" + workspace_root +"' '" + comment + 
                           "' -suppress_push True -commit_date '" + x.CreationDate.ToString() + "'")
    print psi.Arguments
    psi.UseShellExecute = False
    p = Process.Start(psi)
    p.WaitForExit()
    
    cur_version = x.ChangesetId
    