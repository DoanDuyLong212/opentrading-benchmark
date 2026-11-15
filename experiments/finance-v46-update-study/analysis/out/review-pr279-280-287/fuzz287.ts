import { mathOnlyCommand as ok } from "./wt-pr287/src/core/tools/shell/math.ts"
const B={kind:"bash"} as any, P={kind:"powershell"} as any
const bad:[string,any][]=[
 [`awk 'BEGIN{print 1 > "f"}'`,B],[`awk 'BEGIN{x=1; print x > x}'`,B],[`awk 'BEGIN{print 1 | "sh"}'`,B],
 [`awk 'BEGIN{system("id")}'`,B],[`awk 'BEGIN{x = system("id")}'`,B],[`awk 'BEGIN{"id" | getline x}'`,B],
 [`awk 'BEGIN{getline x < "/etc/passwd"}'`,B],[`awk 'BEGIN{x = ENVIRON["HOME"]; print x}'`,B],
 [`awk 'BEGIN{printf "%s\\n", 1}'`,B],[`awk 'BEGIN{printf "%c", 65}'`,B],[`awk 'BEGIN{printf "%1$d\\n", 1}'`,B],
 [`awk 'BEGIN{print "\\033[2J"}'`,B],[`awk 'BEGIN{print "a\\"b"}'`,B],
 [`awk 'BEGIN{while(1){}}'`,B],[`awk 'BEGIN{for(;;)x=1}'`,B],[`awk 'BEGIN{x=1}' /etc/passwd`,B],
 [`awk -f x 'BEGIN{x=1}'`,B],[`awk 'BEGIN{x=1}{print}'`,B],[`awk 'BEGIN{x=1}END{print x}'`,B],
 [`awk 'BEGIN{x=1}'; id`,B],[`awk 'BEGIN{x=1}' && id`,B],[`awk 'BEGIN{x=1}' # '; id`,B],
 [`awk 'BEGIN{print $0}'`,B],[`awk 'BEGIN{@include "x"}'`,B],[`awk 'BEGIN{x = 1 \\\n + 2; print x}'`,B],
 [`awk 'BEGIN{print y}'`,B],[`awk 'BEGIN{NF = 3; print NF}'`,B],[`awk 'BEGIN{OFMT="%d"; print 1.5}'`,B],
 [`awk 'BEGIN{x="a"; print x}'`,B],[`awk 'BEGIN{print 1 2}'`,B],[`awk 'BEGIN{printf "%d\\n", 1, 2}'`,B],
 [`awk 'BEGIN{print (1) > (2)}'`,B],[`awk 'BEGIN{print(1) > "f"}'`,B],[`awk 'BEGIN{printf("%d\\n", 1) > "f"}'`,B],
 [`awk 'BEGIN{x = srand(); print x}'`,B],[`awk 'BEGIN{x = length(1); print x}'`,B],
 [`awk 'BEGIN{x = 1 #'\nid`,B],[`awk 'BEGIN{print -x}'`,B],[`awk 'BEGIN{a::b = 1}'`,B],
 [`$env:PATH`,P],[`$x = 1; $x.GetType()`,P],[`Get-Date`,P],[`$x = 1; $x | Out-File f`,P],[`$(Get-Date)`,P],
 [`$global:x = 1`,P],[`\${x} = 1`,P],[`@(1,2)`,P],[`1..3`,P],[`$x = 1; & $x`,P],[`[System.IO.File]::Delete("x")`,P],
 [`$ErrorActionPreference = 0`,P],[`$x = 1; iex $x`,P],[`<# c #> 1`,P],[`1 -gt 0`,P],[`$x = 1 # c\nGet-Date`,P],
 [`% 1`,P],[`1\n% 2`,P],[`$_ = 1`,P],[`$MaximumVariableCount = 1`,P],[`$x = 1; $x = $x`,P],
]
const good:[string,any][]=[
 [`awk 'BEGIN{ g = 128.4/112 - 1; printf "%.10g %.10g\\n", g*100, (1+g)^3 }'`,B],
 [`awk 'BEGIN{\nk=250/119;\na=log(66.3/73.5)*k; b=log(74.0/81.33)*k\nprintf "%.4f %.4f\\n", a, b\n}'`,B],
 [`awk 'BEGIN { printf("%.2f\\n", 1/3) }'`,B],[`awk 'BEGIN{printf "%.0f\\n%.0f\\n", 1, 2}'`,B],
 [`$g = 128.4/112 - 1; $g*100; [math]::Pow(1 + $g, 3)`,P],
]
let fail=0
for(const [c,s] of bad){ if(ok(c,s)){fail++;console.log('ACCEPTED (bad):',JSON.stringify(c))} }
for(const [c,s] of good){ if(!ok(c,s)){console.log('REJECTED (good):',JSON.stringify(c))} }
console.log(`bad accepted: ${fail}/${bad.length}`)
