#!/usr/bin/env bun
/** Pure arithmetic bridge. Python validates all financial refs against its actual session ledger first. */
import {calculate} from '../../experiments/opentrading-runtime/src/core/tools/calculate'
import {nonFormulaLiterals,FORMULA_CONSTANTS,checkSourceBindings} from '../../experiments/opentrading-runtime/src/core/tools/calculate/expression'
try {
 const input=JSON.parse(await Bun.stdin.text())
 if(typeof input.expression!=='string'||!Array.isArray(input.variables)||!input.variables.length)throw new Error('Expected expression and nonempty source-bound variables')
 const constants=nonFormulaLiterals(input.expression)
 if(constants.length)throw new Error('Financial numeric literals are forbidden; use source variables. Formula constants: '+FORMULA_CONSTANTS.join(','))
 const values:Record<string,{value:number;unit:string;ref?:string}>={}
 for(const variable of input.variables){
  if(typeof variable.name!=='string'||!/^[\p{L}_][\p{L}\p{N}_]*$/u.test(variable.name)||variable.name in values||typeof variable.value!=='number'||!Number.isFinite(variable.value)||typeof variable.unit!=='string')throw new Error('Invalid or duplicate source variable')
  values[variable.name]={value:variable.value,unit:variable.unit,...(typeof variable.ref==='string'?{ref:variable.ref}:{})}
 }
 if(input.output_unit!==undefined&&typeof input.output_unit!=='string')throw new Error('output_unit must be a string')
 if(input.precision!==undefined&&(!Number.isInteger(input.precision)||input.precision<0||input.precision>12))throw new Error('precision must be0..12')
 checkSourceBindings(input.expression,Object.keys(values))
 const result=calculate({expression:input.expression,values,unit:input.output_unit,decimals:input.precision})
 process.stdout.write(JSON.stringify({ok:true,...result}))
}catch(error){process.stdout.write(JSON.stringify({ok:false,error:{code:'invalid_derivation',message:error instanceof Error?error.message:String(error)}}));process.exitCode=1}
