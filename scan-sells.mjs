// Read-only, conservative BSC mainnet scan for direct FLAPJAX treasury-to-pool transfers.
// Superset window 2026-10-10 21:30 UTC to 2026-10-14 00:37 UTC covers all of Oct 11-13 UTC.
// Run with node scan-sells.mjs > sell-scan.json. Fails closed on incomplete RPC reads.
import fs from 'node:fs';
const rpcUrl="https://rpc-bsc.48.club";
const token="0x90c8889f428F9Ebb77BB8f15CAD3a50a9aC680df".toLowerCase();
const treasury="0x7C34E9e21eE28A49Ff0b84B61774119E6633359f".toLowerCase();
const pool="0xcA93EC685b8623688E6B236f9068034B298c2150".toLowerCase();
const transferTopic="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
const padAddr=s=>"0x"+s.slice(2).padStart(64,"0");
const fromBlock=126900000,toBlock=127500000,step=4900;
const spans=[];
for(let lo=fromBlock;lo<=toBlock;lo+=step)spans.push([lo,Math.min(lo+step-1,toBlock)]);
let count=0,failures=0;
async function readSpan([lo,hi]) {
 let error;
 for(let k=0;k<4;k++) {
  try{
   const filter={address:token,fromBlock:"0x"+lo.toString(16),toBlock:"0x"+hi.toString(16),topics:[transferTopic,padAddr(treasury),padAddr(pool)]};
   const response=await fetch(rpcUrl,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({jsonrpc:"2.0",id:lo,method:"eth_getLogs",params:[filter]}),signal:AbortSignal.timeout(15000)});
   if(!response.ok)throw Error("HTTP "+response.status);
   const data=await response.json();
   if(data.error)throw Error(data.error.message);
   if(!Array.isArray(data.result))throw Error("No log array");
   count++;
   return {lo,hi,logs:data.result.map(l=>({blockNumber:Number(BigInt(l.blockNumber)),transactionHash:l.transactionHash,data:l.data,topics:l.topics}))};
  } catch(e){error=e; failures++; await new Promise(done=>setTimeout(done,800*(k+1)));}
 }
 throw Error("Incomplete scan at "+lo+"-"+hi+": "+error?.message);
}
const queue=[...spans], results=[];
async function worker() {
 while(queue.length) {
  const range=queue.shift();const result=await readSpan(range);
  results.push(result);
  await new Promise(done=>setTimeout(done,220));
 }
}
await Promise.all([worker(),worker()]);
results.sort((a,b)=>a.lo-b.lo);
if(results.length!==spans.length||results[0].lo!==fromBlock||results.at(-1).hi!==toBlock)throw Error("Incomplete coverage");
for(let i=1;i<results.length;i++)if(results[i].lo!==results[i-1].hi+1)throw Error("Range gap");
const found=results.flatMap(r=>r.logs);
const evidence={
  chain:"BSC mainnet",rpc:rpcUrl,method:"eth_getLogs",token,from:treasury,to:pool,
  filterTopics:[transferTopic,padAddr(treasury),padAddr(pool)],
  scannedBlockStart:fromBlock,scannedBlockEnd:toBlock,
  timeStartUTC:"2026-10-10T21:30:15.000Z",timeEndUTC:"2026-10-14T00:37:54.000Z",
  requiredWindowUTC:"2026-10-11T00:00:00Z to 2026-10-13T23:59:59Z",
  segments:results.length,failedAttemptRetries:failures,completed:true,matchedTransferCount:found.length,matchedTransfers:found
};
process.stdout.write(JSON.stringify(evidence,null,2)+"\n");
