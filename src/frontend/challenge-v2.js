/* Shared authenticated plan. Never synthesizes AI approval or stores tokens in browser storage. */
(() => {
  "use strict";
  const root = document.querySelector("[data-challenge-v2]");
  if (!root) return;
  const homeParent=root.parentElement;
  const esc = x => String(x ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const proofLabel = {T1:"사진 조건 검토",T2:"기록 제출",T3:"자가 체크"};
  const levelLabel = {E:"쉬움",M:"보통",H:"도전"};
  const statusLabel = {assigned:"기록 준비",in_progress:"진행 중",submitted:"검토 대기",completed:"완료",not_required:"기록 제출 완료",pending:"검토 대기",passed:"사진 조건 확인",needs_retry:"재제출 필요",inconclusive:"판단 어려움"};
  const reasonLabel = {real_visual_review_unavailable:"실제 사진 검토가 준비되지 않아 체크형 대안을 제공합니다.",photo_consent_or_accessibility:"사진 동의·촬영 가능 조건에 맞춰 대체했습니다.",difficulty_safety_or_preference_limit:"안전·선호에 맞춰 난이도를 조정했습니다.",proof_mix_safety_accessibility_or_weekly_limit:"안전·접근성·주간 제한으로 기본 인증 구성을 조정했습니다.",replacement_accessibility:"촬영 접근성 대체",replacement_safety:"안전 대체",replacement_too_hard:"난이도 낮춤",replacement_preference:"선호 변경"};
  let token=null, plan=null, busy=false;
  const channel=typeof BroadcastChannel==="function"?new BroadcastChannel("challenge-v2-refresh"):null;
  window.ForestChallengeV2={enabled:false,plan:null};
  async function api(path,options={}) {
    token=window.challengeV2TokenProvider?.()||token;
    if (!token) {
      const auth=await fetch("/api/v1/auth/token/refresh",{credentials:"same-origin",cache:"no-store"});
      if (!auth.ok) throw new Error("메인 화면에서 로그인하고 이용 가능 확인·건강정보 동의를 마쳐 주세요.");
      token=(await auth.json()).access_token;
    }
    const headers={Authorization:`Bearer ${token}`};
    if (options.body && !(options.body instanceof FormData)) headers["Content-Type"]="application/json";
    const response=await fetch(`/api/v1/challenge-v2${path}`,{...options,headers,credentials:"same-origin",cache:"no-store"});
    const result=await response.json();
    if (!response.ok) {if(response.status===401)token=null;throw new Error(typeof result.detail==="string"?result.detail:"입력값을 확인해 주세요. 저장하지 못했습니다.");}
    return result.data;
  }
  const input=(name,label,type="text",extra="")=>`<label>${label}<input name="${name}" type="${type}" ${extra} required></label>`;
  function settings(p={}) {
    const check=(name,label,fallback=false)=>`<label class="v2-check"><input type="checkbox" name="${name}" ${(p[name]??fallback)?"checked":""}>${label}</label>`;
    return `<details data-settings ${!plan?.enrolled?"open":""}><summary>챌린지 설정·안전 조건</summary><form data-preferences>
      <label>챌린지 방식<select name="mode">${Object.entries({balanced:"균형",activity_focus:"운동 중심",diet_focus:"식단 중심"}).map(([k,v])=>`<option value="${k}" ${p.mode===k?"selected":""}>${v}</option>`).join("")}</select></label>
      <label>가능한 최대 난이도<select name="max_difficulty">${Object.entries(levelLabel).map(([k,v])=>`<option value="${k}" ${(p.max_difficulty||"E")===k?"selected":""}>${v}</option>`).join("")}</select></label>
      ${input("planned_meals","오늘 예정된 식사 횟수","number",`min="0" max="3" value="${p.planned_meals??1}"`)}
      ${input("sugary_drink_opportunities","평소 당 음료 기회(없으면 0)","number",`min="0" max="3" value="${p.sugary_drink_opportunities??0}"`)}
      ${check("safety_confirmed","아래 안전 조건을 확인했어요")}${check("exercise_allowed","통증·낙상 위험·운동 제한 없이 편안히 걸을 수 있어요")}
      ${check("dietary_changes_allowed","의료진 지침 안에서 식사 구성을 바꿀 수 있어요")}${check("fluid_restriction","수분 제한이 있거나 아직 몰라요",true)}
      ${check("swallowing_restriction","씹기·삼키기 제한이 있거나 아직 몰라요",true)}${check("therapeutic_diet","치료식이 필요하거나 아직 몰라요",true)}${check("food_allergy","음식 알레르기가 있거나 아직 몰라요",true)}
      ${check("photo_accessible","사진·활동기록 화면을 제출할 수 있어요")}${check("photo_consent","사진 비공개 보관(최대 7일)과 T1 지정 담당자 검토에 동의해요 (선택)")}
      <p>외부 AI로 사진을 보내지 않습니다. 사진을 거부해도 체크형 대안을 이용할 수 있어요. 타인·개인정보가 찍힌 사진은 피하세요. 사진 동의 해제 후 저장하면 보관 사진을 삭제합니다.</p>
      <label class="v2-check"><input type="checkbox" name="transition_consent" required>기존 기록·보상을 유지하는 V2 전환에 동의해요</label>
      <p>진행 중인 기존 주기가 있으면 내일부터 시작합니다. 새 선호는 다음 배정부터, 안전 제한은 즉시 적용합니다.</p><button>설정 저장</button></form></details>`;
  }
  function sessionForm(item,index) {
    const g=item.goal, current=new Date(Date.now()+9*3600000).toISOString().slice(0,16);
    return `<details><summary>회차 ${index} 기록</summary><form data-session="${item.id}" data-index="${index}">
      ${input("performed_at","수행 시각 (한국 시간, 활동은 종료 시각)","datetime-local",`value="${current}"`)}
      ${g.goal_unit==="minute"?input("quantity","이번 회차 시간(분)","number",`min="${g.per_session_quantity}" max="1440"`):""}
      ${g.family_id==="H02"?input("intake_ml",`${["오전","오후","저녁"][index-1]} 구간 실제 섭취량(mL)`,"number",'min="0" max="20000"')+'<small>이전 구간과 겹치지 않는 양만 기록하세요. 0mL도 정상이며 더 마실 필요가 없습니다.</small>':""}
      ${g.domain==="diet"?'<label>내용 기록<textarea name="note" maxlength="500" required></textarea></label>':""}
      ${g.family_id==="D02"?input("serving_amount","표시 기준량","number",'min="0.01" step="any"')+'<label>기준 단위<select name="serving_unit"><option>g</option><option>mL</option></select></label>'+input("sugar_g","당류(g)","number",'min="0" step="any"')+(g.difficulty!=="E"?input("carbohydrate_g","총탄수화물(g)","number",'min="0" step="any"')+input("product_category","제품 종류","text",'maxlength="80"'):""):""}
      ${["D02","D03"].includes(g.family_id)&&g.difficulty==="H"&&index===g.target_sessions?`<label>${g.family_id==="D02"?"동일 100g 또는 100mL 기준 비교":"다음 날 개선점 한 줄"}<textarea name="improvement" maxlength="200" required></textarea></label>`:""}
      <label class="v2-check"><input name="done" type="checkbox" required>이 회차를 직접 수행하고 기록했어요</label><button>회차 저장</button></form></details>`;
  }
  function card(item) {
    const g=item.goal;
    const uploads=Array.from({length:g.required_uploads},(_,i)=>{
      const proof=item.evidence.find(x=>x.index===i+1);
      return `<form data-upload="${item.id}" data-index="${i+1}">${input("photo",`인증 ${i+1}${proof?` · ${proof.expired?"보관 만료":statusLabel[proof.status]}`:""}`,"file",'accept="image/jpeg,image/png,image/webp"')}<button>사진 제출</button></form>`;
    }).join("");
    return `<article class="v2-card"><div class="v2-tags"><span>${({diet:"식단",activity:"운동",routine:"생활관리"})[g.domain]}</span><span>${levelLabel[g.difficulty]}</span><span>${proofLabel[g.proof_type]}</span></div>
      <h4>${esc(g.title)}</h4><p>목표 ${g.per_session_quantity}${g.goal_unit==="minute"?"분":"회 기록"} × ${g.target_sessions}회</p>
      <strong>회차 ${item.completed_sessions}/${g.target_sessions}${g.goal_unit==="minute"?` · 총 ${item.total_quantity}/${g.per_session_quantity*g.target_sessions}분`:""} · ${statusLabel[item.status]}</strong><progress max="${g.target_sessions}" value="${item.completed_sessions}" aria-label="회차 진행률"></progress>
      ${item.verification_status==="pending"?'<p class="v2-notice">사진 조건 검토 대기 중입니다. 완료·보상은 확인 후 지급됩니다.</p>':""}
      ${["inconclusive","needs_retry"].includes(item.verification_status)?'<p class="v2-notice">사진 조건을 확인하기 어렵습니다. 배정일 안에 다시 제출하거나 체크형 대안을 선택해 주세요.</p>':""}
      <p class="v2-safety">${esc(g.safety)}</p>
      ${item.status!=="completed"?Array.from({length:g.target_sessions},(_,i)=>item.sessions.some(s=>s.index===i+1)?`<small>회차 ${i+1} 저장됨</small>`:sessionForm(item,i+1)).join("")+uploads+`<button type="button" data-alternatives="${item.id}">다른 챌린지로 바꾸기</button><div data-options="${item.id}"></div>`:`<p>${g.proof_type==="T1"?"사진 조건 확인":g.proof_type==="T2"?"기록 제출 완료":"자가 기록 완료"} · 당근 10개 지급</p>`}
      <details><summary>근거·확인 범위</summary><p>목표 수치는 앱 시작용 설계이며 예방 효과의 순위가 아닙니다. 사진으로 실제 섭취나 걷기 진위를 증명하지 않습니다.</p>${g.sources.map(s=>`<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a>`).join(" · ")}</details></article>`;
  }
  function render() {
    root.innerHTML=`<header class="v2-heading"><h3>당뇨 예방 챌린지</h3><button data-refresh type="button">새로고침</button></header><p data-message role="status" aria-live="polite"></p><p class="v2-safety">시범 운영 · 수행률은 진단·처방이나 질병 개선을 의미하지 않습니다.</p>
      ${(plan?.proof_mix_exception_reason||[]).map(r=>`<p class="v2-notice">${esc(reasonLabel[r]||r)}</p>`).join("")}
      ${(plan?.substitutions||[]).map(()=>'<p class="v2-notice">당 음료 대체 대신 같은 난이도의 수분 기록을 배정했어요. 추가 섭취는 필요하지 않아요.</p>').join("")}
      ${settings(plan?.preferences)}<div class="v2-cards">${(plan?.items||[]).map(card).join("")}</div>
      ${plan?.enrolled?`<p>오늘 ${plan.completed||0}/${plan.items.length}개 완료${!plan.day_id?` · 시작일 ${esc(plan.starts_on)}`:""}</p>`:""}
      ${plan?.day_id?`<p class="v2-wallet">계정 당근 ${plan.carrot_balance??100}개 · ${plan.chest_issued?"일일 보물상자 지급 완료":"활성 카드 모두 완료하면 일일 보물상자 지급"}</p><small>기존 숲 체험용 당근·아이템 기록은 삭제하거나 합산하지 않습니다.</small>`:""}<a href="/">로그인·이용 가능 확인으로 이동</a>`;
    window.ForestChallengeV2.plan=plan;
    if(root.parentElement.matches('[data-step="7"]'))root.insertAdjacentHTML("beforeend",'<button type="button" data-dashboard>대시보드로 이동</button>');
    window.dispatchEvent(new CustomEvent("challenge-v2-updated",{detail:plan}));
  }
  const notify=message=>{root.querySelector("[data-message]").textContent=message;};
  async function load() {
    if(busy)return;busy=true;
    try {plan=await api("/today",{method:"POST"});render();} catch(error){render();notify(error.message);} finally{busy=false;}
  }
  root.addEventListener("click",async event=>{
    if(event.target.closest("[data-refresh]"))return load();
    if(event.target.closest("[data-dashboard]"))return window.dispatchEvent(new Event("challenge-v2-open-dashboard"));
    const button=event.target.closest("[data-alternatives]");if(!button)return;
    try {
      const {items}=await api(`/assignments/${button.dataset.alternatives}/alternatives`);
      root.querySelector(`[data-options="${button.dataset.alternatives}"]`).innerHTML=`<form data-replace="${button.dataset.alternatives}"><label>대체 카드<select name="template_code" required>${items.map(x=>`<option value="${x.code}">${levelLabel[x.difficulty]} · ${proofLabel[x.proof_type]} · ${esc(x.title)}</option>`).join("")}</select></label><label>변경 이유<select name="reason"><option value="accessibility">촬영 접근성</option><option value="too_hard">난이도 낮추기</option><option value="safety">안전 제한</option><option value="preference">선호 변경</option></select></label><p>이전 기록은 보존하고 새 카드에서 다시 시작합니다. 완료된 슬롯은 바꾸지 않습니다.</p><button ${items.length?"":"disabled"}>대체 확정</button></form>`;
    }catch(error){notify(error.message);}
  });
  root.addEventListener("submit",async event=>{
    event.preventDefault();if(busy)return;
    const form=event.target,data=new FormData(form),values=Object.fromEntries(data);
    busy=true;const buttons=[...form.querySelectorAll("button")];buttons.forEach(b=>b.disabled=true);
    try {
      if(form.matches("[data-preferences]")) {
        for(const input of form.querySelectorAll('input[type="checkbox"]'))values[input.name]=input.checked;
        values.planned_meals=Number(values.planned_meals);values.sugary_drink_opportunities=Number(values.sugary_drink_opportunities);
        await api("/preferences",{method:"PUT",body:JSON.stringify(values)});plan=await api("/today",{method:"POST"});
      }else if(form.matches("[data-session]")) {
        values.done=true;values.performed_at=new Date(`${values.performed_at}:00+09:00`).toISOString();
        for(const key of ["quantity","intake_ml","serving_amount","sugar_g","carbohydrate_g"])if(key in values)values[key]=Number(values[key]);
        plan={...plan,...await api(`/assignments/${form.dataset.session}/sessions/${form.dataset.index}`,{method:"PUT",body:JSON.stringify(values)})};
      }else if(form.matches("[data-upload]")) {
        if(data.get("photo").size>10*1024*1024)throw new Error("사진은 10MB 이하로 올려 주세요.");
        plan={...plan,...await api(`/assignments/${form.dataset.upload}/evidence/${form.dataset.index}`,{method:"PUT",body:data})};
      }else if(form.matches("[data-replace]")) {
        plan={...plan,...await api(`/assignments/${form.dataset.replace}/replacement`,{method:"PATCH",body:JSON.stringify(values)})};
      }
      render();notify("서버에 저장했습니다.");channel?.postMessage("refresh");
    }catch(error){notify(error.message);}finally{busy=false;buttons.forEach(b=>b.disabled=false);}
  });
  window.addEventListener("challenge-v2-auth",()=>{token=null;load();});
  document.addEventListener("visibilitychange",()=>{if(!document.hidden&&!root.contains(document.activeElement))load();});
  window.addEventListener("challenge-v2-step",event=>{
    if(!window.ForestChallengeV2.enabled)return;
    if(event.detail===7) {
      document.querySelector("#challenge-form")?.before(root);
      if(!root.querySelector("[data-dashboard]"))root.insertAdjacentHTML("beforeend",'<button type="button" data-dashboard>대시보드로 이동</button>');
      const title=document.querySelector("#challenge-title");if(title)title.textContent="나에게 맞는 일일 챌린지를 설정해요";
    } else if(event.detail===8) homeParent.prepend(root);
  });
  if(channel)channel.onmessage=()=>{if(!root.contains(document.activeElement))load();};
  fetch("/api/v1/challenge-v2/capabilities",{cache:"no-store"}).then(r=>r.json()).then(result=>{
    if(!result.data.enabled){root.hidden=true;return;}
    window.ForestChallengeV2.enabled=true;document.documentElement.classList.add("challenge-v2-enabled");root.hidden=false;load();
  }).catch(()=>{root.hidden=false;root.textContent="챌린지 서버 연결을 확인해 주세요. 오프라인 완료는 저장하지 않습니다.";});
})();
