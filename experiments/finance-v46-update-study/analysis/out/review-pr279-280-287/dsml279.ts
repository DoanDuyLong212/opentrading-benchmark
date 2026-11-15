import { stripMarkup } from "./wt-pr279/src/core/loop/markup.ts"
for (const f of ["fin-c1-chg-402__opentrading_baseline__r2.final.txt","fin-c4-rebal-426__opentrading_baseline__r2.final.txt"]) {
  const t = await Bun.file(f).text(); const r = stripMarkup(t); console.log(f.slice(0,24), "in", t.length, "-> out", JSON.stringify(r.text), r.tags) }
const shellCase = '\n<｜DSML｜ calls>\n<｜DSML｜ invoke name="shell">\n<｜DSML｜ parameter name="command" string="true">python3 -c "print((21.0/24.64)**(250/119)-1)"</｜DSML｜ parameter>\n</｜DSML｜ invoke>\n</｜DSML｜ calls>'
console.log("6ae8db9-smoke", JSON.stringify(stripMarkup(shellCase).text), stripMarkup(shellCase).tags)
const mixed = 'Kết quả: {"values":{"x":1}}\n<｜DSML｜ calls><｜DSML｜ invoke name="shell"></｜DSML｜ invoke></｜DSML｜ calls>'
console.log("answer+dsml", JSON.stringify(stripMarkup(mixed).text))
