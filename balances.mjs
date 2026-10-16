// Independent read-only treasury balance cross-check at the three receipt blocks.
const rpcUrls=["https://bsc-dataseed.bnbchain.org","https://rpc-bsc.48.club","https://bsc-mainnet.public.blastapi.io"];
let i=0;
async function rpc(method,params){
  let failure;
  for(const endpoint of rpcUrls){
    try{
      const r=await fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({jsonrpc:"2.0",id:++i,method,params}),signal:AbortSignal.timeout(12500)});
      const j=await r.json();
      if(!r.ok||j.error||j.result===undefined||j.result===null)throw Error(j.error?.message||("HTTP "+r.status));
      return {result:j.result,endpoint};
    }catch(e){failure=e}
  }
  throw Error(method+": "+failure?.message);
}
const token="0x90c8889f428F9Ebb77BB8f15CAD3a50a9aC680df";
const treasury="0x7C34E9e21eE28A49Ff0b84B61774119E6633359f";
const pool="0xcA93EC685b8623688E6B236f9068034B298c2150";
const pad=s=>s.slice(2).toLowerCase().padStart(64,"0");
const txHashes=[
 "0x82d01172ae26f1c86287643e123af1675ca5c18b984b7740c1a0c1647d2801eb",
 "0x9afdc96e3ca876b5b617a26ba5105012ed8c33e805c77b1616bf48c198d5cbf1",
 "0xc94de373d1fb00093431224a97475b3b2b48b9a4962d15acbe9d9c5c016d720c"
];
const out=[];
for(const hash of txHashes){
 const tx=(await rpc("eth_getTransactionByHash",[hash])).result;
 const receipt=(await rpc("eth_getTransactionReceipt",[hash])).result;
 const block=tx.blockNumber;
 const txBlock=(await rpc("eth_getBlockByNumber",[block,false])).result;
 const rawBNB=(await rpc("eth_getBalance",[treasury,block])).result;
 const rawToken=(await rpc("eth_call",[{to:token,data:"0x70a08231"+pad(treasury)},block])).result;
 const rawPoolToken=(await rpc("eth_call",[{to:token,data:"0x70a08231"+pad(pool)},block])).result;
 out.push({hash,blockNumber:Number(BigInt(block)),blockTimestamp:new Date(Number(BigInt(txBlock.timestamp))*1000).toISOString(),
  receiptStatus:Number(BigInt(receipt.status)),treasuryBnbWei:BigInt(rawBNB).toString(),
  treasuryTokenWei:BigInt(rawToken).toString(),poolTokenWei:BigInt(rawPoolToken).toString(),
  swapValueWei:BigInt(tx.value).toString(),gasUsed:BigInt(receipt.gasUsed).toString(),
  effectiveGasPriceWei:BigInt(receipt.effectiveGasPrice||tx.gasPrice).toString()});
}
process.stdout.write(JSON.stringify({chain:"BSC",balances:out},null,2)+"\n");
