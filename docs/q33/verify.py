#!/usr/bin/env python3
"""VM5 original public BSC FLAPJAX Q33 independent read-only source audit.
No wallet signing/reads, user USDC monitoring, private keys, token purchase,
referral posting, Taskmarket submissions or platform authentication.
Only third-party public token addresses, sponsor public ledger and JSON-RPC.
"""
from __future__ import annotations
import argparse, concurrent.futures, datetime as dt, hashlib, html, json, os, re, tempfile, time, urllib.request
from collections import defaultdict, Counter
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"docs/q33/proof-recreated.json"
TOKEN="0x90c8889f428f9ebb77bb8f15cad3a50a9ac680df"
TREAS="0x7c34e9e21ee28a49ff0b84b61774119e6633359f"
POOL="0xca93ec685b8623688e6b236f9068034b298c2150"
TOPIC="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
RPC="https://bsc-dataseed.bnbchain.org"
LEDGER="https://flapjax.surge.sh/"
INDEX="https://api.gopluslabs.io/api/v1/token_security/56?contract_addresses="+TOKEN
TRANSFER_TOKEN_DECIMALS=18
MAX_ITEMS=300
HEAD_MARGIN=64

def read(url,raw=False,timeout=18):
    assert url in (LEDGER,INDEX)
    req=urllib.request.Request(url,headers={"Accept":"application/json,text/html","User-Agent":"vm5-original-one-owner-Q33-public-BSC-audit-20261019"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        assert r.status==200 and r.geturl()==url
        body=r.read(500000)
        if len(body)==500000:raise ValueError("public source cap")
        return body.decode("utf-8","replace") if raw else json.loads(body)
def check_addr(x):
    if not isinstance(x,str) or re.fullmatch("0x[0-9a-fA-F]{40}",x) is None:raise ValueError("invalid address")
    return x.lower()
def dec18(raw):
    if not isinstance(raw,int) or raw<0:raise ValueError("bad amount")
    return str(Decimal(raw)/10**TRANSFER_TOKEN_DECIMALS)
def to_percentage(raw,supply):
    if supply<=0:raise ValueError("invalid supply")
    return str((Decimal(raw)*100)/Decimal(supply))
def parse_published(html_raw):
    chunks=re.findall(r'<li class="fjx-c-item">(.*?)</li>',html_raw,re.S)
    if not 30<=len(chunks)<=MAX_ITEMS:raise ValueError("no complete sponsor ledger")
    rows=[]
    for chunk in chunks:
        label=re.search(r'<span class="fjx-c-meta">(.*?)</span>',chunk,re.S)
        anchor=re.search(r'https://bscscan\.com/tx/(0x[a-fA-F0-9]{64})',chunk,re.I)
        if not label or not anchor:continue
        v=" ".join(html.unescape(re.sub(r'<[^>]*>',' ',label.group(1))).split())
        m=re.search(r'2026-10-(\d\d)\s*·\s*(.*?)\s*·\s*tx\s',v,re.I)
        if not m:continue
        day=int(m.group(1)); task=m.group(2).strip()
        if 12<=day<=17 and re.search(r'Q\d+',task,re.I):
            amount=re.search(r'<span class="fjx-c-amt">\s*([0-9,.]+)\s+FLAPJAX\s*</span>',chunk,re.I|re.S)
            nominal=Decimal(amount.group(1).replace(",","")) if amount else None
            rows.append({"day":day,"kind":task,"tx":anchor.group(1).lower(),
                "sponsorDeclaredAmountFLAPJAX":str(nominal) if nominal is not None else None})
    if len(rows)<25:raise ValueError("sponsor source did not give enough receipt entries")
    unique={}
    for r in rows:
        if r["tx"] not in unique:unique[r["tx"]]=r
        elif unique[r["tx"]]!=r:raise ValueError("conflicting original sponsor rows")
    return list(unique.values()),len(chunks)
def rpc_batch(calls):
    # Explicitly public third-party token/transaction reads only: no wallet/key/owner balance queries.
    payload=[{"jsonrpc":"2.0","id":i+1,"method":m,"params":p} for i,(m,p) in enumerate(calls)]
    body=json.dumps(payload if len(payload)>1 else payload[0],separators=(",",":")).encode()
    req=urllib.request.Request(RPC,data=body,method="POST",
        headers={"Content-Type":"application/json","Accept":"application/json","User-Agent":"vm5-readonly-public-BSC-Q33-audit"})
    with urllib.request.urlopen(req,timeout=26) as r:
        if r.status!=200:raise ValueError("public RPC HTTP failure")
        result=json.load(r)
    result=result if isinstance(result,list) else [result]
    byid={x["id"]:x for x in result}
    if len(byid)!=len(calls):raise ValueError("incomplete RPC batch")
    output=[]
    for i in range(1,len(calls)+1):
        x=byid[i]
        if "error" in x or "result" not in x or x["result"] is None:
            raise ValueError("RPC data unavailable or rate limited")
        output.append(x["result"])
    return output
def batches(items,size):
    return [items[i:i+size] for i in range(0,len(items),size)]
def receipt_transfer(receipt,expected_token=TOKEN,expected_from=TREAS):
    if receipt.get("status")!="0x1" or not receipt.get("blockNumber"):
        raise ValueError("unmined or failed official sponsor tx")
    matches=[]
    for l in receipt.get("logs") or []:
        if check_addr(l.get("address"))!=expected_token:continue
        topics=l.get("topics") or []
        if len(topics)!=3 or topics[0].lower()!=TOPIC:continue
        frm=check_addr("0x"+topics[1][-40:])
        to=check_addr("0x"+topics[2][-40:])
        wei=int(l["data"],16)
        if frm==expected_from:
            matches.append({"to":to,"rawAmount":wei,"amountFLAPJAX":dec18(wei),
                "from":frm,"logIndex":int(l["logIndex"],16)})
    return matches
def save(out,record):
    out.parent.mkdir(mode=0o750,exist_ok=True,parents=True)
    fd,p=tempfile.mkstemp(dir=out.parent,prefix=".vm5-q33-evidence-")
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(record,f,indent=2,ensure_ascii=False);f.write("\n")
            f.flush();os.fsync(f.fileno())
        os.replace(p,out)
    finally:
        if os.path.exists(p):os.unlink(p)
def offline_tests():
    examples=[{"day":12,"kind":"quick task Q18","tx":"0x"+"a"*64,"sponsorDeclaredAmountFLAPJAX":"250000"}]
    h='<ul><li class="fjx-c-item"><span class="fjx-c-amt">250,000 FLAPJAX</span><span class="fjx-c-meta">2026-10-12 · quick task Q18 · <a href="https://bscscan.com/tx/0x'+("a"*64)+'">tx</a></span></li></ul>'
    assert dec18(250000*10**18)=="250000"
    assert to_percentage(50,100)=="50"
    for invalid in ("0xff","0x"+"x"*40,None):
        try:check_addr(invalid)
        except ValueError:pass
        else:raise AssertionError("invalid address not rejected")
    test={"status":"0x1","blockNumber":"0x8","logs":[{"address":TOKEN,"topics":[TOPIC,"0x"+TREAS[2:].rjust(64,"0"),"0x"+("b"*40).rjust(64,"0")],"data":hex(250000*10**18),"logIndex":"0x2"}]}
    assert receipt_transfer(test)[0]["amountFLAPJAX"]=="250000"
    for key,val in (("status","0x0"),("blockNumber",None)):
        corrupted=dict(test);corrupted[key]=val
        try:receipt_transfer(corrupted)
        except ValueError:pass
        else:raise AssertionError("bad receipt not rejected")
    try:dec18(-2)
    except ValueError:pass
    else:raise AssertionError("negative token value accepted")
    print(json.dumps({"selftest":"PASS","cases":9,"network":False,"privateKeyOrWalletReads":False}))
def collect():
    clock=dt.datetime.now(dt.timezone.utc)
    h=read(LEDGER,raw=True)
    entries,n_source=parse_published(h)
    index=read(INDEX)
    if index.get("code")!=1:raise ValueError("index code not healthy")
    tok=index.get("result",{}).get(TOKEN)
    if not isinstance(tok,dict) or tok.get("token_symbol")!="FLAPJAX":raise ValueError("wrong token index")
    indexed=tok.get("holders") or []
    if len(indexed)!=10:raise ValueError("full top10 not exposed")
    head_hex=rpc_batch([("eth_blockNumber",[])])[0]
    network=rpc_batch([("eth_chainId",[])])[0]
    if int(network,16)!=56:raise ValueError("wrong BSC mainnet")
    snapshot=int(head_hex,16)-HEAD_MARGIN
    print(json.dumps({"phase":"sponsor+index+chain_verified","sponsorReceiptRows":len(entries),
        "sponsorOriginalLedgerRows":n_source,"indexHoldersReported":tok.get("holder_count"),"snapshotBlock":snapshot}),flush=True)
    # ~80 unique Qxx sponsor-recited payout tx; demand 1 full onchain receipt per distinct tx.
    calls=[("eth_getTransactionReceipt",[e["tx"]]) for e in entries]
    pieces=batches(calls,17)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        returned=list(pool.map(rpc_batch,pieces))
    receipts=[x for chunk in returned for x in chunk]
    if len(receipts)!=len(entries):raise ValueError("incomplete receipt coverage")
    payouts=defaultdict(int);observed=[];errors=[]
    for e,r in zip(entries,receipts):
        if r.get("transactionHash","").lower()!=e["tx"]:
            raise ValueError("tx-hash mismatch")
        block=int(r["blockNumber"],16)
        if block>snapshot:raise ValueError("not finalized at audit snapshot")
        txouts=receipt_transfer(r)
        payout_total=sum(x["rawAmount"] for x in txouts)
        declared=e["sponsorDeclaredAmountFLAPJAX"]
        exact_declared=None if declared is None else Decimal(payout_total)/10**18==Decimal(declared)
        if not txouts:errors.append({"tx":e["tx"],"problem":"No FLAPJAX Transfer from treasury in purported payout"})
        if exact_declared is False:errors.append({"tx":e["tx"],"problem":"Sponsor nominal differs from all treasury transfers in tx"})
        for x in txouts:payouts[x["to"]]+=x["rawAmount"]
        observed.append({**e,"blockNumber":block,"receiptStatus":"success","treasuryTransfers":txouts,
                         "declaredMatchesAllTreasuryTransfers":exact_declared})
    recipients=sorted(payouts)
    top_addrs=[check_addr(z["address"]) for z in indexed]
    addrs=list(dict.fromkeys(top_addrs+[TREAS]+recipients))
    data=[("eth_call",[{"to":TOKEN,"data":"0x18160ddd"},hex(snapshot)])]
    for a in addrs:
        data += [("eth_call",[{"to":TOKEN,"data":"0x70a08231"+a[2:].rjust(64,"0")},hex(snapshot)])]
        if a in top_addrs:
            data += [("eth_getCode",[a,hex(snapshot)])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        response=[v for section in pool.map(rpc_batch,batches(data,16)) for v in section]
    if len(response)!=len(data):raise ValueError("incomplete snapshot onchain reads")
    supply=int(response[0],16)
    values={};code={}
    at=1
    for addr in addrs:
        values[addr]=int(response[at],16);at+=1
        if addr in top_addrs:code[addr]=len(response[at])>2;at+=1
    report_holders=[]
    for i,x in enumerate(indexed):
        a=check_addr(x["address"]); bal=values[a]
        category=("AMM pool (DexScreener confirmed Pancake v3)" if a==POOL
          else "null/destroyed token sink (0xdead; not a wallet with a human controller)" if a=="0x"+"0"*36+"dead"
          else "smart contract, subtype not independently resolved" if code[a] else "EOA/no runtime code")
        report_holders.append({"indexRank":i+1,"address":a,"indexBalance":x.get("balance"),
            "indexShareFraction":x.get("percent"),"snapshotBalance":dec18(bal),
            "snapshotSupplyPercent":to_percentage(bal,supply),
            "chainHasRuntimeContractCode":code[a],"category":category})
    # Avoid inventing an onchain holder enumeration: GoPlus counts its own latest index
    # while all supplied top10 balances are pinned to one independently verified BSC block.
    retained=[]
    for addr,earned in sorted(payouts.items()):
        bal=values[addr]
        retained.append({"address":addr,"QxxPayoutsTotal":dec18(earned),
           "onchainBalanceAtSnapshot":dec18(bal),"stillHoldsAtLeastCumulativeNumericPayout":bal>=earned})
    verified=len([r for r in retained if r["stillHoldsAtLeastCumulativeNumericPayout"]])
    eligible=len(retained)
    report={
        "sourceKind":"independent read-only VM5 chain-audited public task evidence, no claim/submission",
        "auditedAtUTC":dt.datetime.now(dt.timezone.utc).isoformat(),
        "taskId":"0x21ce4da5892dda87559f8c15ea6a4504deeeac510f73fd658efc63276754bd97",
        "token":TOKEN,"treasury":TREAS,"pool":POOL,
        "publicSources":{"sponsorLedger":LEDGER,"index":INDEX,"publicChainJSONRPC":RPC},
        "snapshot":{"chainId":56,"blockNumber":snapshot,"observedHeadAtRead":int(head_hex,16),
                     "confirmationsAtRead":HEAD_MARGIN,"totalSupply":dec18(supply)},
        "indexSnapshot":{"readAfterUTC":clock.isoformat(),
            "reporter":"GoPlus token_security BSC - NOT a complete historical event replay",
            "holderCountReported":tok.get("holder_count"),
            "holderCountAtExactPinnedBlockIndependentlyEnumerated":False,
            "top10Count":len(indexed)},
        "topTenWithPinnedChainBalances":report_holders,
        "treasuryPinned":{"balanceFLAPJAX":dec18(values[TREAS]),"shareSupplyPercent":to_percentage(values[TREAS],supply)},
        "sponsorPayoutWindow":{"start":"2026-10-12","end":"2026-10-17",
            "scope":"sponsor public ledger rows with Q-number labels; not proved COMPLETE for all issued campaign transfers",
            "originalPublicSponsorLedgerRows":n_source,
            "uniqueQSeriesTxsAttempted":len(entries),"confirmedWithTreasuryFLAPJAXTransfers":len(entries)-len([e for e in observed if not e["treasuryTransfers"]]),
            "distinctRecipientsConfirmed":eligible,"walletsRetainAtLeastOwnNumericPayoutAtPinnedBlock":verified,
            "walletsBelowOwnCumulativePayoutAtPinnedBlock":eligible-verified,
            "retentionDefinition":"balance >= sum of that wallet's indexed FLAPJAX Q-series rewards. Fungible tokens cannot prove same original coins never moved.",
            "entries":observed,"recipientChecks":retained},
        "treasuryBuybacksVsPayoutsClaim":{
            "statement":"treasury only receives buybacks and sends bounties, never sells to pool",
            "verifiedSubset":"All listed Q-series payout transaction receipts decoded. Existing prior Q25 verified Oct11-13 direct treasury-to-pool logs absent in 123 complete ranges 126900000..127500000, separate historical limited evidence.",
            "definitiveAllHistoryClaimVerified":False,
            "note":"No comprehensive mint-to-snapshot treasury token Transfer-log replay in this report. Do not mark all-time claim confirmed, or assert no sells globally."},
        "sourceDiscrepancies":errors,"sourceReproducible":True,
        "no_wallet_secrets_or_signatures_or_funds":True,
        "payerBuyerRewardActuallyReceivedToVM5":"0 VERIFIED",
        "noTaskmarketSubmissionPerformed":True
    }
    save(OUT,report)
    print(json.dumps({"evidence":str(OUT),"snapshotBlock":snapshot,"indexHolderCount":tok.get("holder_count"),
        "top10":len(indexed),"verifiedSponsorQSeriesTxs":len(entries),
        "distinctRecipients":eligible,"numericRetainedCount":verified,"evidenceDiscrepancies":len(errors),
        "definitiveSponsorAllTimeNoSaleProof":False,"actualVM5USDCReceipt":0}),flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--selftest",action="store_true")
    a=parser.parse_args()
    if a.selftest:return offline_tests()
    collect()
if __name__=="__main__":main()
