// Original, read-only BSC verification. No wallet or secret is used.
// Run: node verify.mjs > chain-evidence.json
const hosts=["https://bsc-dataseed.bnbchain.org","https://bsc-rpc.publicnode.com","https://bsc-mainnet.public.blastapi.io"];
const token="0x90c8889f428F9Ebb77BB8f15CAD3a50a9aC680df".toLowerCase();
const pool="0xcA93EC685b8623688E6B236f9068034B298c2150".toLowerCase();
const treasury="0x7C34E9e21eE28A49Ff0b84B61774119E6633359f".toLowerCase();
const txs=["0x9afdc96e3ca876b5b617a26ba5105012ed8c33e805c77b1616bf48c198d5cbf1","0xc94de373d1fb00093431224a97475b3b2b48b9a4962d15acbe9d9c5c016d720c"];
const transferTopic="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
const hexb=x=>Number(BigInt(x));
const callArgs=(address,data,block="latest")=>[{to:address,data},block];
const countState={count:0};
async function rpc(method,params){
  let lastError;
  for(let i=0;i<hosts.length;i++){
    const host=hosts[(countState.count+i)%hosts.length];
    try{
      const rsp=await fetch(host,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({jsonrpc:"2.0",id:++countState.count,method,params}),signal:AbortSignal.timeout(11000)});
      if(!rsp.ok)throw Error("HTTP "+rsp.status);
      const data=await rsp.json();
      if(data.error)throw Error(data.error.message||JSON.stringify(data.error));
      if(data.result===undefined||data.result===null)throw Error("missing result");
      return {result:data.result,host};
    } catch(e) {lastError=e}
  }
  throw Error(method+" failed on all hosts: "+(lastError?.message||"unknown"));
}
const qty=x=>BigInt(x).toString();
const signedTick=x=>Number(BigInt.asIntN(24,BigInt(x)));
async function slot0(n){
 const block="0x"+n.toString(16);
 const c=await rpc("eth_call",callArgs(pool,"0x3850c7bd",block));
 const s=c.result.replace(/^0x/,"");
 if(s.length<128)throw Error("bad slot0 response");
 return {blockNumber:n,sqrtPriceX96:BigInt("0x"+s.slice(0,64)).toString(),tick:signedTick("0x"+s.slice(64,128)),rpc:c.host};
}
const out={chain:"BSC",chainId:(await rpc("eth_chainId",[])).result,token,pool,treasury,buys:[]};
for(const hash of txs){
 const tx=(await rpc("eth_getTransactionByHash",[hash])).result;
 const receipt=(await rpc("eth_getTransactionReceipt",[hash])).result;
 if(tx.hash.toLowerCase()!==hash||receipt.transactionHash.toLowerCase()!==hash||tx.blockHash.toLowerCase()!==receipt.blockHash.toLowerCase())throw Error("mismatched tx and receipt");
 const n=hexb(tx.blockNumber);
 const b=(await rpc("eth_getBlockByNumber",[tx.blockNumber,false])).result;
 if(b.hash.toLowerCase()!==tx.blockHash.toLowerCase())throw Error("noncanonical block");
 const received=[];
 for(const log of receipt.logs){
  if(log.address.toLowerCase()!==token||log.topics[0]?.toLowerCase()!==transferTopic)continue;
  const from="0x"+log.topics[1].slice(-40),to="0x"+log.topics[2].slice(-40);
  if(from.toLowerCase()===pool&&to.toLowerCase()===treasury)received.push({from:from.toLowerCase(),to:to.toLowerCase(),rawWei:qty(log.data),logIndex:hexb(log.logIndex)});
 }
 out.buys.push({
  hash,blockNumber:n,timestamp:new Date(hexb(b.timestamp)*1000).toISOString(),txValueWei:qty(tx.value),
  txFrom:tx.from.toLowerCase(),txTo:tx.to.toLowerCase(),receiptStatus:hexb(receipt.status),
  receiptLogCount:receipt.logs.length,received,
  priceBefore:await slot0(n-1),priceAt:await slot0(n)
 });
}
const token0=(await rpc("eth_call",callArgs(pool,"0x0dfe1681"))).result;
const token1=(await rpc("eth_call",callArgs(pool,"0xd21220a7"))).result;
const decimals=(await rpc("eth_call",callArgs(token,"0x313ce567"))).result;
out.poolToken0="0x"+token0.slice(-40).toLowerCase();
out.poolToken1="0x"+token1.slice(-40).toLowerCase();
out.tokenDecimals=hexb(decimals);
process.stdout.write(JSON.stringify(out,null,2)+"\n");
