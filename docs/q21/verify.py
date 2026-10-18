#!/usr/bin/env python3
"""VM5 ORIGINAL FlapJax Q21 buyback — public EXTERNAL buyer receipt audit.

Read-only only: one specific non-owner public BSC transaction, public named
pool contract eth_call at two blocks and third-party treasury at the buy block.
NEVER touch a user wallet balance, key, sign, spend gas, alter blockchain,
register accounts or run an owner wallet transaction watcher.
"""
from __future__ import annotations
from decimal import Decimal, getcontext
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request,urlopen
import json,os,re,sys,tempfile
getcontext().prec=80
ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/"docs/q21/proof-replayed-local.json"
NODE="https://bsc-mainnet.public.blastapi.io"
TX="0x82d01172ae26f1c86287643e123af1675ca5c18b984b7740c1a0c1647d2801eb"
TOKEN="0x90c8889f428f9ebb77bb8f15cad3a50a9ac680df"
POOL="0xca93ec685b8623688e6b236f9068034b298c2150"
TREASURY="0x7c34e9e21ee28a49ff0b84b61774119e6633359f"
ROUTER="0x1b81d678ffb9c0263b24a97847620c99d213eb14"
WBNB="0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
TOPIC="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
BLOCK=127067713
Q96=Decimal(2)**96
def decraw(raw,decimals=18):
    return str(Decimal(raw)/(10**decimals))
def parse_slot(data):
    if not isinstance(data,str) or not data.startswith("0x") or len(data)!=450:
        raise ValueError("slot0 bytes not canonical")
    h=data[2:]
    sqrt=int(h[:64],16)
    tick=int(h[64:128],16)&((1<<24)-1)
    if tick >= 1<<23:tick-=1<<24
    if sqrt<=0:raise ValueError("invalid sqrt")
    return sqrt,tick,(Decimal(sqrt)/Q96)**2
def rpc_batch(queries):
    payload=[{"jsonrpc":"2.0","id":i+1,"method":m,"params":p} for i,(m,p) in enumerate(queries)]
    req=Request(NODE,data=json.dumps(payload).encode(),method="POST",
      headers={"Content-Type":"application/json","Accept":"application/json",
        "User-Agent":"vm5-public-SINGLE-thirdparty-FlapJax-Q21-audit-not-user-wallet"})
    with urlopen(req,timeout=22) as r:
        if r.status!=200:raise ValueError("archive node not available")
        rows=json.load(r)
    if not isinstance(rows,list) or len(rows)!=len(payload):
        raise ValueError("incomplete RPC batch")
    byid={z["id"]:z for z in rows}
    vals=[]
    for i in range(1,len(queries)+1):
        row=byid[i]
        if "error" in row or row.get("result") is None:raise ValueError("archive query incomplete")
        vals.append(row["result"])
    return vals
def atomic(out,obj):
    out.parent.mkdir(parents=True,exist_ok=True)
    fd,p=tempfile.mkstemp(dir=out.parent,prefix=".flapjax-q21-readonly-")
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"w",encoding="utf8") as f:
            json.dump(obj,f,ensure_ascii=False,indent=2);f.write("\n")
            f.flush();os.fsync(f.fileno())
        os.replace(p,out)
    finally:
        if os.path.exists(p):os.unlink(p)
def selftest():
    assert decraw(10**16)=="0.01"
    assert decraw(23907253965589989685035768)=="23907253.965589989685035768"
    assert Decimal(23907254)-Decimal(decraw(23907253965589989685035768))==Decimal("0.034410010314964232")
    assert Decimal("0.000000000413")<((Decimal(1611027302170866092493120)/Q96)**2)<Decimal("0.000000000414")
    assert 127067713-1==127067712
    assert TOKEN!=TREASURY and POOL!=TREASURY
    print(json.dumps({"selftest":"PASS","assertions":6,"noUserWalletOrSecrets":True,"noSignedActionsOrGas":True}))
def run():
    q=[("eth_chainId",[]),("eth_blockNumber",[]),
       ("eth_getTransactionByHash",[TX]),("eth_getTransactionReceipt",[TX]),
       ("eth_getBlockByNumber",[hex(BLOCK),False]),
       ("eth_call",[{"to":POOL,"data":"0x3850c7bd"},hex(BLOCK-1)]),
       ("eth_call",[{"to":POOL,"data":"0x3850c7bd"},hex(BLOCK)]),
       ("eth_getBalance",[TREASURY,hex(BLOCK)]),
       ("eth_call",[{"to":TOKEN,"data":"0x70a08231"+TREASURY[2:].rjust(64,"0")},hex(BLOCK)]),
       ("eth_call",[{"to":POOL,"data":"0x0dfe1681"},hex(BLOCK)]),
       ("eth_call",[{"to":POOL,"data":"0xd21220a7"},hex(BLOCK)]),
       ("eth_call",[{"to":POOL,"data":"0xddca3f43"},hex(BLOCK)])]
    ch,head,tx,rc,block,pre,post,treasbnb,treasfj,t0,t1,fee=rpc_batch(q)
    assert int(ch,16)==56 and int(head,16)>BLOCK+64
    assert tx["hash"].lower()==TX and int(tx["blockNumber"],16)==BLOCK
    assert tx["from"].lower()==TREASURY and tx["to"].lower()==ROUTER
    assert rc["transactionHash"].lower()==TX and rc["status"]=="0x1"
    assert int(rc["blockNumber"],16)==BLOCK and int(block["number"],16)==BLOCK
    assert ("0x"+t0[-40:].lower())==TOKEN and ("0x"+t1[-40:].lower())==WBNB
    assert int(fee,16)==10000
    transfers=[z for z in rc["logs"]
       if z["address"].lower()==TOKEN and len(z.get("topics") or [])==3
       and z["topics"][0].lower()==TOPIC
       and z["topics"][1][-40:].lower()==POOL[2:]
       and z["topics"][2][-40:].lower()==TREASURY[2:]]
    if len(transfers)!=1:raise ValueError("not one canonical sponsor incoming transfer")
    amt=int(transfers[0]["data"],16)
    if amt!=23907253965589989685035768:raise ValueError("wrong canonical buyback amount")
    wei=int(tx["value"],16)
    if wei!=10**16:raise ValueError("not sponsor declared 0.01 BNB")
    before_sqrt,before_tick,before_price=parse_slot(pre)
    after_sqrt,after_tick,after_price=parse_slot(post)
    if before_tick!=-216076 or after_tick!=-216045:raise ValueError("expected historic slot0 ticks changed")
    fj=Decimal(amt)/Decimal(10**18)
    delta=Decimal(23907254)-fj
    pricechange=(after_price/before_price-1)*100
    bnblast=Decimal(int(treasbnb,16))/Decimal(10**18)
    fjlast=Decimal(int(treasfj,16))/Decimal(10**18)
    assert abs(bnblast-Decimal("0.1446"))<Decimal("0.00005")
    assert abs(fjlast-Decimal("237237298"))<Decimal("0.5")
    proof={
      "kind":"Independent THIRD-PARTY BSC blockchain receipt validation; no claim or payout yet",
      "sourceAuthor":"livastic-vm5-primary-20260911 (original agent disclosure)",
      "observedUTC":datetime.now(timezone.utc).isoformat(),
      "network":"BNB Smart Chain mainnet","chainId":56,"canonicalFjToken":TOKEN,
      "originalSponsorThread":"https://thecolony.ai/post/28acbdea-449b-4717-9517-6619a94247c8",
      "originalUgigQ21Bounty":"https://ugig.net/bounties/9aac4845-540f-4c88-849a-62ea0cd4d076",
      "sourcePublicRPC":NODE,"txHash":TX,"bscscan":"https://bscscan.com/tx/"+TX,
      "blockNumber":BLOCK,"blockDateUTC":datetime.fromtimestamp(int(block["timestamp"],16),timezone.utc).isoformat(),
      "headObserved":int(head,16),"confirmationsAtAudit":int(head,16)-BLOCK,
      "sponsorTreasury":TREASURY,"swapRouter":ROUTER,"pool":POOL,
      "poolFeeBps":100,"token0":TOKEN,"token1":WBNB,
      "nativeBNBSentWei":str(wei),"nativeBNBSent":decraw(wei),
      "transactionGasUsed":int(rc["gasUsed"],16),
      "gasPriceWei":str(int(rc["effectiveGasPrice"],16)),
      "gasFeeBNB":decraw(int(rc["gasUsed"],16)*int(rc["effectiveGasPrice"],16)),
      "FJTransferFromPoolToTreasuryLogIndex":int(transfers[0]["logIndex"],16),
      "receivedFlapjaxRawWei":str(amt),"receivedFlapjaxExact":str(fj),
      "sponsorReceiptedFlapjaxWhole":23907254,
      "sponsorRoundingMinusExactFj":str(delta),
      "poolSlot0BlockBefore":BLOCK-1,
      "poolSlot0SqrtPriceX96Before":str(before_sqrt),
      "poolSlot0TickBefore":before_tick,
      "poolSlot0SqrtPriceX96After":str(after_sqrt),
      "poolSlot0TickAfter":after_tick,
      "preBuyWBNBperFj":str(before_price),"postBuyWBNBperFj":str(after_price),
      "preBuyFjPerBNB":str(Decimal(1)/before_price),
      "impactWBNBperFjPct":str(pricechange),
      "impactFjPerBNBPct":str((before_price/after_price-1)*100),
      "treasuryBNBAtBuyBlock":str(bnblast),"treasuryFlapjaxAtBuyBlock":str(fjlast),
      "publishedSponsorTreasuryBNBApprox":"0.1446",
      "publishedSponsorTreasuryFJWhole":237237298,
      "verdict":{
        "txHash":"MATCH","block":"MATCH to BscScan and mainnet receipt",
        "nativeBNBSpend":"MATCH exact 0.01",
        "tokenRecipient":"MATCH treasury from exact indexed ERC20 transfer",
        "FLAPJAXAmount":"MATCH sponsor whole-number rounding (exact differs by 0.034410010314964232)",
        "poolVenue":"MATCH Pancake V3 token0/token1 and 1% fee onchain",
        "preBuySlot0Price":"INDEPENDENT ARCHIVE-READ MATCH: read exact block 127067712",
        "treasuryBNBPostBalance":"MATCH at sponsor shown 4 decimal rounding",
        "treasuryFJPostBalance":"MATCH sponsor nearest-whole rounding",
        "allHistoryNoTreasurySaleClaim":"OUTSIDE Q21 scope and NOT PROVED"
      },
      "noFjClaimFiledByVM5Yet":True,
      "noFjPaymentReceivedYet":True,
      "ownerActualNewCashAttributedToThisReportUSD":"0",
      "noUserEvmWalletOrPrivateKeyOrGasReadOrUsed":True
    }
    atomic(OUTPUT,proof)
    print(json.dumps({"auditedQ21OriginalTx":TX,"block":BLOCK,
        "independentPreBuySlot0Block":BLOCK-1,"flapjaxReceived":str(fj),
        "bnbSpent":str(Decimal(wei)/Decimal(10**18)),
        "priceChangePct":str(pricechange.quantize(Decimal(".000001"))),
        "sponsorRoundedToWholeFjDifference":str(delta),
        "realReceivedByVM5Flapjax":0,
        "output":str(OUTPUT)},ensure_ascii=False))
if __name__=="__main__":selftest() if "--selftest" in sys.argv else run()
