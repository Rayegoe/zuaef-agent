(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const i of document.querySelectorAll('link[rel="modulepreload"]'))n(i);new MutationObserver(i=>{for(const r of i)if(r.type==="childList")for(const a of r.addedNodes)a.tagName==="LINK"&&a.rel==="modulepreload"&&n(a)}).observe(document,{childList:!0,subtree:!0});function s(i){const r={};return i.integrity&&(r.integrity=i.integrity),i.referrerPolicy&&(r.referrerPolicy=i.referrerPolicy),i.crossOrigin==="use-credentials"?r.credentials="include":i.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function n(i){if(i.ep)return;i.ep=!0;const r=s(i);fetch(i.href,r)}})();const it=globalThis,ft=it.ShadowRoot&&(it.ShadyCSS===void 0||it.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,vt=Symbol(),wt=new WeakMap;let Nt=class{constructor(t,s,n){if(this._$cssResult$=!0,n!==vt)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=s}get styleSheet(){let t=this.o;const s=this.t;if(ft&&t===void 0){const n=s!==void 0&&s.length===1;n&&(t=wt.get(s)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),n&&wt.set(s,t))}return t}toString(){return this.cssText}};const Bt=e=>new Nt(typeof e=="string"?e:e+"",void 0,vt),k=(e,...t)=>{const s=e.length===1?e[0]:t.reduce((n,i,r)=>n+(a=>{if(a._$cssResult$===!0)return a.cssText;if(typeof a=="number")return a;throw Error("Value passed to 'css' function must be a 'css' function result: "+a+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[r+1],e[0]);return new Nt(s,e,vt)},Wt=(e,t)=>{if(ft)e.adoptedStyleSheets=t.map(s=>s instanceof CSSStyleSheet?s:s.styleSheet);else for(const s of t){const n=document.createElement("style"),i=it.litNonce;i!==void 0&&n.setAttribute("nonce",i),n.textContent=s.cssText,e.appendChild(n)}},zt=ft?e=>e:e=>e instanceof CSSStyleSheet?(t=>{let s="";for(const n of t.cssRules)s+=n.cssText;return Bt(s)})(e):e;const{is:Zt,defineProperty:Jt,getOwnPropertyDescriptor:Kt,getOwnPropertyNames:Yt,getOwnPropertySymbols:Xt,getPrototypeOf:Qt}=Object,dt=globalThis,At=dt.trustedTypes,te=At?At.emptyScript:"",ee=dt.reactiveElementPolyfillSupport,Z=(e,t)=>e,ot={toAttribute(e,t){switch(t){case Boolean:e=e?te:null;break;case Object:case Array:e=e==null?e:JSON.stringify(e)}return e},fromAttribute(e,t){let s=e;switch(t){case Boolean:s=e!==null;break;case Number:s=e===null?null:Number(e);break;case Object:case Array:try{s=JSON.parse(e)}catch{s=null}}return s}},mt=(e,t)=>!Zt(e,t),Et={attribute:!0,type:String,converter:ot,reflect:!1,useDefault:!1,hasChanged:mt};Symbol.metadata??=Symbol("metadata"),dt.litPropertyMetadata??=new WeakMap;let D=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,s=Et){if(s.state&&(s.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((s=Object.create(s)).wrapped=!0),this.elementProperties.set(t,s),!s.noAccessor){const n=Symbol(),i=this.getPropertyDescriptor(t,n,s);i!==void 0&&Jt(this.prototype,t,i)}}static getPropertyDescriptor(t,s,n){const{get:i,set:r}=Kt(this.prototype,t)??{get(){return this[s]},set(a){this[s]=a}};return{get:i,set(a){const c=i?.call(this);r?.call(this,a),this.requestUpdate(t,c,n)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??Et}static _$Ei(){if(this.hasOwnProperty(Z("elementProperties")))return;const t=Qt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(Z("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(Z("properties"))){const s=this.properties,n=[...Yt(s),...Xt(s)];for(const i of n)this.createProperty(i,s[i])}const t=this[Symbol.metadata];if(t!==null){const s=litPropertyMetadata.get(t);if(s!==void 0)for(const[n,i]of s)this.elementProperties.set(n,i)}this._$Eh=new Map;for(const[s,n]of this.elementProperties){const i=this._$Eu(s,n);i!==void 0&&this._$Eh.set(i,s)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const s=[];if(Array.isArray(t)){const n=new Set(t.flat(1/0).reverse());for(const i of n)s.unshift(zt(i))}else t!==void 0&&s.push(zt(t));return s}static _$Eu(t,s){const n=s.attribute;return n===!1?void 0:typeof n=="string"?n:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,s=this.constructor.elementProperties;for(const n of s.keys())this.hasOwnProperty(n)&&(t.set(n,this[n]),delete this[n]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Wt(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,s,n){this._$AK(t,n)}_$ET(t,s){const n=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,n);if(i!==void 0&&n.reflect===!0){const r=(n.converter?.toAttribute!==void 0?n.converter:ot).toAttribute(s,n.type);this._$Em=t,r==null?this.removeAttribute(i):this.setAttribute(i,r),this._$Em=null}}_$AK(t,s){const n=this.constructor,i=n._$Eh.get(t);if(i!==void 0&&this._$Em!==i){const r=n.getPropertyOptions(i),a=typeof r.converter=="function"?{fromAttribute:r.converter}:r.converter?.fromAttribute!==void 0?r.converter:ot;this._$Em=i;const c=a.fromAttribute(s,r.type);this[i]=c??this._$Ej?.get(i)??c,this._$Em=null}}requestUpdate(t,s,n,i=!1,r){if(t!==void 0){const a=this.constructor;if(i===!1&&(r=this[t]),n??=a.getPropertyOptions(t),!((n.hasChanged??mt)(r,s)||n.useDefault&&n.reflect&&r===this._$Ej?.get(t)&&!this.hasAttribute(a._$Eu(t,n))))return;this.C(t,s,n)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,s,{useDefault:n,reflect:i,wrapped:r},a){n&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,a??s??this[t]),r!==!0||a!==void 0)||(this._$AL.has(t)||(this.hasUpdated||n||(s=void 0),this._$AL.set(t,s)),i===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(s){Promise.reject(s)}const t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[i,r]of this._$Ep)this[i]=r;this._$Ep=void 0}const n=this.constructor.elementProperties;if(n.size>0)for(const[i,r]of n){const{wrapped:a}=r,c=this[i];a!==!0||this._$AL.has(i)||c===void 0||this.C(i,void 0,r,c)}}let t=!1;const s=this._$AL;try{t=this.shouldUpdate(s),t?(this.willUpdate(s),this._$EO?.forEach(n=>n.hostUpdate?.()),this.update(s)):this._$EM()}catch(n){throw t=!1,this._$EM(),n}t&&this._$AE(s)}willUpdate(t){}_$AE(t){this._$EO?.forEach(s=>s.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(s=>this._$ET(s,this[s])),this._$EM()}updated(t){}firstUpdated(t){}};D.elementStyles=[],D.shadowRootOptions={mode:"open"},D[Z("elementProperties")]=new Map,D[Z("finalized")]=new Map,ee?.({ReactiveElement:D}),(dt.reactiveElementVersions??=[]).push("2.1.2");const gt=globalThis,kt=e=>e,at=gt.trustedTypes,Rt=at?at.createPolicy("lit-html",{createHTML:e=>e}):void 0,Lt="$lit$",S=`lit$${Math.random().toFixed(9).slice(2)}$`,Mt="?"+S,se=`<${Mt}>`,U=document,J=()=>U.createComment(""),K=e=>e===null||typeof e!="object"&&typeof e!="function",$t=Array.isArray,ne=e=>$t(e)||typeof e?.[Symbol.iterator]=="function",pt=`[ 	
\f\r]`,B=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,St=/-->/g,Pt=/>/g,I=RegExp(`>|${pt}(?:([^\\s"'>=/]+)(${pt}*=${pt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Tt=/'/g,It=/"/g,Dt=/^(?:script|style|textarea|title)$/i,ie=e=>(t,...s)=>({_$litType$:e,strings:t,values:s}),o=ie(1),V=Symbol.for("lit-noChange"),d=Symbol.for("lit-nothing"),Ot=new WeakMap,C=U.createTreeWalker(U,129);function qt(e,t){if(!$t(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return Rt!==void 0?Rt.createHTML(t):t}const re=(e,t)=>{const s=e.length-1,n=[];let i,r=t===2?"<svg>":t===3?"<math>":"",a=B;for(let c=0;c<s;c++){const l=e[c];let f,v,p=-1,_=0;for(;_<l.length&&(a.lastIndex=_,v=a.exec(l),v!==null);)_=a.lastIndex,a===B?v[1]==="!--"?a=St:v[1]!==void 0?a=Pt:v[2]!==void 0?(Dt.test(v[2])&&(i=RegExp("</"+v[2],"g")),a=I):v[3]!==void 0&&(a=I):a===I?v[0]===">"?(a=i??B,p=-1):v[1]===void 0?p=-2:(p=a.lastIndex-v[2].length,f=v[1],a=v[3]===void 0?I:v[3]==='"'?It:Tt):a===It||a===Tt?a=I:a===St||a===Pt?a=B:(a=I,i=void 0);const w=a===I&&e[c+1].startsWith("/>")?" ":"";r+=a===B?l+se:p>=0?(n.push(f),l.slice(0,p)+Lt+l.slice(p)+S+w):l+S+(p===-2?c:w)}return[qt(e,r+(e[s]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),n]};class Y{constructor({strings:t,_$litType$:s},n){let i;this.parts=[];let r=0,a=0;const c=t.length-1,l=this.parts,[f,v]=re(t,s);if(this.el=Y.createElement(f,n),C.currentNode=this.el.content,s===2||s===3){const p=this.el.content.firstChild;p.replaceWith(...p.childNodes)}for(;(i=C.nextNode())!==null&&l.length<c;){if(i.nodeType===1){if(i.hasAttributes())for(const p of i.getAttributeNames())if(p.endsWith(Lt)){const _=v[a++],w=i.getAttribute(p).split(S),L=/([.?@])?(.*)/.exec(_);l.push({type:1,index:r,name:L[2],strings:w,ctor:L[1]==="."?ae:L[1]==="?"?le:L[1]==="@"?de:ct}),i.removeAttribute(p)}else p.startsWith(S)&&(l.push({type:6,index:r}),i.removeAttribute(p));if(Dt.test(i.tagName)){const p=i.textContent.split(S),_=p.length-1;if(_>0){i.textContent=at?at.emptyScript:"";for(let w=0;w<_;w++)i.append(p[w],J()),C.nextNode(),l.push({type:2,index:++r});i.append(p[_],J())}}}else if(i.nodeType===8)if(i.data===Mt)l.push({type:2,index:r});else{let p=-1;for(;(p=i.data.indexOf(S,p+1))!==-1;)l.push({type:7,index:r}),p+=S.length-1}r++}}static createElement(t,s){const n=U.createElement("template");return n.innerHTML=t,n}}function H(e,t,s=e,n){if(t===V)return t;let i=n!==void 0?s._$Co?.[n]:s._$Cl;const r=K(t)?void 0:t._$litDirective$;return i?.constructor!==r&&(i?._$AO?.(!1),r===void 0?i=void 0:(i=new r(e),i._$AT(e,s,n)),n!==void 0?(s._$Co??=[])[n]=i:s._$Cl=i),i!==void 0&&(t=H(e,i._$AS(e,t.values),i,n)),t}class oe{constructor(t,s){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=s}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:s},parts:n}=this._$AD,i=(t?.creationScope??U).importNode(s,!0);C.currentNode=i;let r=C.nextNode(),a=0,c=0,l=n[0];for(;l!==void 0;){if(a===l.index){let f;l.type===2?f=new et(r,r.nextSibling,this,t):l.type===1?f=new l.ctor(r,l.name,l.strings,this,t):l.type===6&&(f=new ce(r,this,t)),this._$AV.push(f),l=n[++c]}a!==l?.index&&(r=C.nextNode(),a++)}return C.currentNode=U,i}p(t){let s=0;for(const n of this._$AV)n!==void 0&&(n.strings!==void 0?(n._$AI(t,n,s),s+=n.strings.length-2):n._$AI(t[s])),s++}}class et{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,s,n,i){this.type=2,this._$AH=d,this._$AN=void 0,this._$AA=t,this._$AB=s,this._$AM=n,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const s=this._$AM;return s!==void 0&&t?.nodeType===11&&(t=s.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,s=this){t=H(this,t,s),K(t)?t===d||t==null||t===""?(this._$AH!==d&&this._$AR(),this._$AH=d):t!==this._$AH&&t!==V&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):ne(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==d&&K(this._$AH)?this._$AA.nextSibling.data=t:this.T(U.createTextNode(t)),this._$AH=t}$(t){const{values:s,_$litType$:n}=t,i=typeof n=="number"?this._$AC(t):(n.el===void 0&&(n.el=Y.createElement(qt(n.h,n.h[0]),this.options)),n);if(this._$AH?._$AD===i)this._$AH.p(s);else{const r=new oe(i,this),a=r.u(this.options);r.p(s),this.T(a),this._$AH=r}}_$AC(t){let s=Ot.get(t.strings);return s===void 0&&Ot.set(t.strings,s=new Y(t)),s}k(t){$t(this._$AH)||(this._$AH=[],this._$AR());const s=this._$AH;let n,i=0;for(const r of t)i===s.length?s.push(n=new et(this.O(J()),this.O(J()),this,this.options)):n=s[i],n._$AI(r),i++;i<s.length&&(this._$AR(n&&n._$AB.nextSibling,i),s.length=i)}_$AR(t=this._$AA.nextSibling,s){for(this._$AP?.(!1,!0,s);t!==this._$AB;){const n=kt(t).nextSibling;kt(t).remove(),t=n}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}}class ct{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,s,n,i,r){this.type=1,this._$AH=d,this._$AN=void 0,this.element=t,this.name=s,this._$AM=i,this.options=r,n.length>2||n[0]!==""||n[1]!==""?(this._$AH=Array(n.length-1).fill(new String),this.strings=n):this._$AH=d}_$AI(t,s=this,n,i){const r=this.strings;let a=!1;if(r===void 0)t=H(this,t,s,0),a=!K(t)||t!==this._$AH&&t!==V,a&&(this._$AH=t);else{const c=t;let l,f;for(t=r[0],l=0;l<r.length-1;l++)f=H(this,c[n+l],s,l),f===V&&(f=this._$AH[l]),a||=!K(f)||f!==this._$AH[l],f===d?t=d:t!==d&&(t+=(f??"")+r[l+1]),this._$AH[l]=f}a&&!i&&this.j(t)}j(t){t===d?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class ae extends ct{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===d?void 0:t}}class le extends ct{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==d)}}class de extends ct{constructor(t,s,n,i,r){super(t,s,n,i,r),this.type=5}_$AI(t,s=this){if((t=H(this,t,s,0)??d)===V)return;const n=this._$AH,i=t===d&&n!==d||t.capture!==n.capture||t.once!==n.once||t.passive!==n.passive,r=t!==d&&(n===d||i);i&&this.element.removeEventListener(this.name,this,n),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class ce{constructor(t,s,n){this.element=t,this.type=6,this._$AN=void 0,this._$AM=s,this.options=n}get _$AU(){return this._$AM._$AU}_$AI(t){H(this,t)}}const ue=gt.litHtmlPolyfillSupport;ue?.(Y,et),(gt.litHtmlVersions??=[]).push("3.3.3");const pe=(e,t,s)=>{const n=s?.renderBefore??t;let i=n._$litPart$;if(i===void 0){const r=s?.renderBefore??null;n._$litPart$=i=new et(t.insertBefore(J(),r),r,void 0,s??{})}return i._$AI(e),i};const bt=globalThis;class b extends D{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const s=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=pe(s,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return V}}b._$litElement$=!0,b.finalized=!0,bt.litElementHydrateSupport?.({LitElement:b});const he=bt.litElementPolyfillSupport;he?.({LitElement:b});(bt.litElementVersions??=[]).push("4.2.2");const R=e=>(t,s)=>{s!==void 0?s.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)};const fe={attribute:!0,type:String,converter:ot,reflect:!1,hasChanged:mt},ve=(e=fe,t,s)=>{const{kind:n,metadata:i}=s;let r=globalThis.litPropertyMetadata.get(i);if(r===void 0&&globalThis.litPropertyMetadata.set(i,r=new Map),n==="setter"&&((e=Object.create(e)).wrapped=!0),r.set(s.name,e),n==="accessor"){const{name:a}=s;return{set(c){const l=t.get.call(this);t.set.call(this,c),this.requestUpdate(a,l,e,!0,c)},init(c){return c!==void 0&&this.C(a,void 0,e,c),c}}}if(n==="setter"){const{name:a}=s;return function(c){const l=this[a];t.call(this,c),this.requestUpdate(a,l,e,!0,c)}}throw Error("Unsupported decorator location: "+n)};function u(e){return(t,s)=>typeof s=="object"?ve(e,t,s):((n,i,r)=>{const a=i.hasOwnProperty(r);return i.constructor.createProperty(r,n),a?Object.getOwnPropertyDescriptor(i,r):void 0})(e,t,s)}function g(e){return u({...e,state:!0,attribute:!1})}class Vt extends Error{constructor(t,s,n){super(s),this.code=t,this.status=n}}async function W(e){const t=await fetch(e);if(!t.ok){let s="INTERNAL_ERROR",n=`HTTP ${t.status}`;try{const i=await t.json();i.error?.code&&(s=i.error.code),i.error?.message&&(n=i.error.message)}catch{}throw new Vt(s,n,t.status)}return await t.json()}async function me(e,t){const s=await fetch(e,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(t)});if(!s.ok){let n="INTERNAL_ERROR",i=`HTTP ${s.status}`;try{const r=await s.json();r.error?.code&&(n=r.error.code),r.error?.message&&(i=r.error.message)}catch{}throw new Vt(n,i,s.status)}return await s.json()}const Ct=200,O={health:()=>W("/api/health"),listRuns:e=>W(e?`/api/runs?limit=${Ct}&cursor=${encodeURIComponent(e)}`:`/api/runs?limit=${Ct}`),getRun:e=>W(`/api/runs/${encodeURIComponent(e)}`),getRunInspection:e=>W(`/api/runs/${encodeURIComponent(e)}/inspection`),getRunAnalysis:e=>W(`/api/runs/${encodeURIComponent(e)}/analysis`),createRunAnalysis:(e,t={})=>me(`/api/runs/${encodeURIComponent(e)}/analysis`,{scope:"full",selected_row_id:t.selectedRowId??null,intent:t.intent??"Diagnose this run for the next smallest engineering experiment.",agent:!0}),runEventsUrl:e=>`/api/runs/${encodeURIComponent(e)}/events`},ge={inspectorView:"run",inspectorTab:"summary"},rt=864e5;function q(e){if(!e)return"";const t=new Date(e);return Number.isNaN(t.getTime())?"":t.toLocaleTimeString(void 0,{hour12:!1})}function jt(e){if(!e)return"";const t=new Date(e);return Number.isNaN(t.getTime())?"":t.toLocaleString(void 0,{year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:!1})}function $e(e,t=Date.now()){if(!e)return"—";const s=new Date(e);if(Number.isNaN(s.getTime()))return"—";const n=t-s.getTime();return n<6e4?"just now":n<36e5?`${Math.floor(n/6e4)}m ago`:n<rt?`${Math.floor(n/36e5)}h ago`:n<7*rt?`${Math.floor(n/rt)}d ago`:s.toLocaleDateString()}function A(e){if(e==null||e<0)return"";const t=e/1e3;if(t<60)return`${t.toFixed(1)}s`;const s=Math.floor(t/60),n=Math.round(t-s*60);return`${s}m${String(n).padStart(2,"0")}s`}function j(e){return typeof e!="number"?"":e>=1e3?`${(e/1e3).toFixed(1)}k`:String(e)}function ht(e){return e==null?"Unknown":e>=1048576?`${(e/1048576).toFixed(1)} MB`:e>=1024?`${(e/1024).toFixed(1)} KB`:`${e} B`}function be(e){if(!e)return"";const t=[],s=j(e.input_tokens),n=j(e.output_tokens);return s&&t.push(`${s} in`),n&&t.push(`${n} out`),t.join(" · ")}function ye(e,t=Date.now()){if(!e.started_at)return"Older";const s=new Date(e.started_at).getTime();if(Number.isNaN(s))return"Older";const n=new Date(t).setHours(0,0,0,0);return s>=n?"Today":s>=n-rt?"Yesterday":"Older"}const Ht={completed:"✓",failed:"✗",paused:"⏸",incomplete:"◔",started:"●",unresolved:"?",unknown:"?",limit_reached:"⏹"};function Gt(e){return e?Ht[e]??"·":""}function _e(e,t){if(t)return e.find(s=>s.id===t)}function xe(e){return"groupId"in e}function we(e){const t=[];let s=0;for(;s<e.length;){const n=e[s];if(n.kind!=="tool_call"){t.push(n),s+=1;continue}let i=s+1;for(;i<e.length&&e[i].kind==="tool_call"&&e[i].title===n.title;)i+=1;i-s>=2?t.push({groupId:`tool-group-${n.id}`,toolName:n.title,rows:e.slice(s,i)}):t.push(n),s=i}return t}function ze(e,t){return t?e.rows.some(s=>s.id===t):!1}const Ae=200;function z(e){if(!e.started_at)return null;const t=Date.parse(e.started_at);return Number.isNaN(t)?null:t}function ut(e){return e.status==="started"}function Ee(e,t){const s=z(e);if(s===null)return null;if(ut(e))return Math.max(t,s);if(e.duration_ms!==null)return s+e.duration_ms;const n=e.finished_at?Date.parse(e.finished_at):NaN;return Number.isNaN(n)||n<s?null:n}function ke(e,t,s){if(t==="input")return e.usage?.input_tokens??null;if(t==="output")return e.usage?.output_tokens??null;const n=z(e);return ut(e)?n===null?null:Math.max(s-n,0):e.duration_ms}function Re(e,t,s){const i=e.filter(h=>h.kind==="model_request"&&z(h)!==null).sort((h,E)=>(z(h)??0)-(z(E)??0)).slice(-60);if(i.length===0)return{bars:[],ticks:[],t0:0,t1:0,span:0};let r=z(i[0])??0;const a=Math.max(...i.map(h=>Ee(h,s)??z(h)??0)),c=h=>{const E=z(h);return h.kind==="tool_call"&&E!==null&&E>=r&&E<=a},l=e.filter(c).slice(0,Ae).map(h=>({row:h,x:0})),f=Math.max(a-r,1),v=h=>Math.min(Math.max((h-r)/f,0),1),p=i.map(h=>ke(h,t,s)),_=p.filter(h=>h!==null),w=Math.max(..._,1),L=i.map((h,E)=>({row:h,x:v(z(h)??r),h:p[E]===null?.04:Math.max(Math.min(p[E]/w,1),.04),value:p[E],active:ut(h)}));for(const h of l)h.x=v(z(h.row)??r);return{bars:L,ticks:l,t0:r,t1:a,span:f}}var Se=Object.defineProperty,Pe=Object.getOwnPropertyDescriptor,yt=(e,t,s,n)=>{for(var i=n>1?void 0:n?Pe(t,s):t,r=e.length-1,a;r>=0;r--)(a=e[r])&&(i=(n?a(t,s,i):a(i))||i);return n&&i&&Se(t,s,i),i};let X=class extends b{constructor(){super(...arguments),this.artifacts=[],this.pause=null}render(){return o`
      <span class="label">Artifact</span>
      ${this.artifacts.length===0?o`<span class="none">No artifacts recorded for this run</span>`:this.artifacts.map(e=>o`<span class="artifact" title=${e.sha256}>
              <span class="path">${e.path}</span>
              <span class="fact">${ht(e.size)}</span>
              <span class="fact">${e.change}</span>
              <span class="fact">sha256:${e.sha256.slice(0,12)}</span>
            </span>`)}
      ${this.pause?o`<span class="pause">
            ⏸ paused — ${this.pause.pending_approvals.length} approval(s) pending
            (supervision not wired in read-only build)
          </span>`:""}
    `}};X.styles=k`
    :host {
      display: flex;
      align-items: center;
      gap: var(--z-space-4);
      padding: var(--z-space-2) var(--z-space-3);
      border-top: 1px solid var(--z-border);
      background: var(--z-surface);
      overflow-x: auto;
      white-space: nowrap;
      flex-shrink: 0;
    }
    .label {
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--z-text-subtle);
      flex-shrink: 0;
    }
    .artifact {
      display: inline-flex;
      align-items: baseline;
      gap: var(--z-space-2);
      font-family: var(--z-font-mono);
      font-size: 12px;
    }
    .path { color: var(--z-text); }
    .fact { color: var(--z-text-muted); font-size: 11px; }
    .none { color: var(--z-text-subtle); font-size: 12px; }
    .pause {
      color: var(--z-warning);
      font-size: 12px;
      border-left: 1px solid var(--z-border);
      padding-left: var(--z-space-4);
      flex-shrink: 0;
    }
  `;yt([u({attribute:!1})],X.prototype,"artifacts",2);yt([u({attribute:!1})],X.prototype,"pause",2);X=yt([R("zuaef-artifact-bar")],X);var Te=Object.defineProperty,Ie=Object.getOwnPropertyDescriptor,Ft=(e,t,s,n)=>{for(var i=n>1?void 0:n?Ie(t,s):t,r=e.length-1,a;r>=0;r--)(a=e[r])&&(i=(n?a(t,s,i):a(i))||i);return n&&i&&Te(t,s,i),i};let lt=class extends b{constructor(){super(...arguments),this.status=""}render(){const e=this.status||"unknown";return o`<span class=${e}
      ><span aria-hidden="true">${Ht[e]??"·"}</span>${e}</span
    >`}};lt.styles=k`
    span {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-family: var(--z-font-mono);
      font-size: 11px;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      white-space: nowrap;
    }
    .failed { color: var(--z-danger); }
    .paused, .limit_reached { color: var(--z-warning); }
    .incomplete, .started { color: var(--z-accent); }
    /* Completed is the normal case — quiet; anomalies carry the color. */
    .completed { color: var(--z-text-subtle); }
    .unknown, .unresolved { color: var(--z-text-muted); }
  `;Ft([u()],lt.prototype,"status",2);lt=Ft([R("zuaef-status-badge")],lt);var Oe=Object.defineProperty,Ce=Object.getOwnPropertyDescriptor,x=(e,t,s,n)=>{for(var i=n>1?void 0:n?Ce(t,s):t,r=e.length-1,a;r>=0;r--)(a=e[r])&&(i=(n?a(t,s,i):a(i))||i);return n&&i&&Oe(t,s,i),i};const Ut=2e3,nt=2e4;let y=class extends b{constructor(){super(...arguments),this.projection=null,this.inspection=null,this.inspectorView="run",this.analysis=null,this.selectedEventId="",this.inspectorTab="summary",this.inspectionLoading=!1,this.inspectionError="",this.analysisLoading=!1,this.analysisError=""}get row(){return _e(this.projection?.timeline??[],this.selectedEventId)}get availableTabs(){const e=this.row;if(!e)return["summary"];const t=["summary"];return(e.payload.response_parts??[]).length>0&&t.push("io"),e.usage&&Object.keys(e.usage).length>0&&t.push("usage"),t.push("raw"),t}setTab(e){this.dispatchEvent(new CustomEvent("tab-selected",{detail:{tab:e},bubbles:!0,composed:!0}))}setView(e){this.dispatchEvent(new CustomEvent("view-selected",{detail:{view:e},bubbles:!0,composed:!0}))}render(){const e=o`<div class="view-tabs" role="tablist" aria-label="Inspector view">
      ${["run","inspection","analysis"].map(i=>o`<button
          role="tab"
          aria-selected=${i===this.inspectorView?"true":"false"}
          @click=${()=>this.setView(i)}
        >
          ${i==="run"?"Run":i==="inspection"?"Inspection":"Analysis"}
        </button>`)}
    </div>`;if(this.inspectorView==="inspection")return o`${e}${this.renderInspection()}`;if(this.inspectorView==="analysis")return o`${e}${this.renderAnalysis()}`;const t=this.availableTabs,s=t.includes(this.inspectorTab)?this.inspectorTab:"summary",n=this.row;return o`${e}
      ${t.length>1?o`<div class="tabs" role="tablist">
            ${t.map(i=>o`<button
                role="tab"
                aria-selected=${i===s?"true":"false"}
                @click=${()=>this.setTab(i)}
              >
                ${je[i]}
              </button>`)}
          </div>`:""}
      <div class="scroll">
        ${n?this.renderEvent(s,n):this.renderRunOverview()}
      </div>
    `}renderInspection(){if(this.inspectionLoading)return o`<div class="scroll"><p class="inspection-note">Loading inspection…</p></div>`;if(this.inspectionError)return o`<div class="scroll"><p class="error-line">${this.inspectionError}</p></div>`;const e=this.inspection;if(!e)return o`<div class="scroll"><p class="inspection-note">Select a run.</p></div>`;const t=e.summary;return o`
      <div class="scroll">
        <h3>Inspection</h3>
        <p class="inspection-note">
          Deterministic facts from the current run projection. Model input/output content is excluded.
        </p>
        <dl>
          <dt>Status</dt>
          <dd><zuaef-status-badge .status=${t.status??""}></zuaef-status-badge></dd>
          <dt>Run ID</dt>
          <dd>${t.run_id??"Unknown"}</dd>
          <dt>Model</dt>
          <dd class=${t.model?"":"none"}>${t.model??"Unknown"}</dd>
          <dt>Profile</dt>
          <dd class=${t.profile?"":"none"}>${t.profile??"Unknown"}</dd>
          <dt>Duration</dt>
          <dd class=${t.duration_ms===null?"none":""}>
            ${t.duration_ms===null?"Unknown":A(t.duration_ms)}
          </dd>
          <dt>Requests</dt><dd>${this.knownNumber(t.requests)}</dd>
          <dt>Tool calls</dt><dd>${this.knownNumber(t.tool_calls)}</dd>
          <dt>Input tokens</dt><dd>${j(t.input_tokens??void 0)||"Unknown"}</dd>
          <dt>Output tokens</dt><dd>${j(t.output_tokens??void 0)||"Unknown"}</dd>
          <dt>Usage basis</dt><dd>${t.usage_source??"Unknown"}</dd>
        </dl>

        ${this.renderRequestRanking("Slowest requests",e.rankings.slowest_requests)}
        ${this.renderRequestRanking("Largest input",e.rankings.largest_input_requests)}
        ${this.renderRequestRanking("Largest output",e.rankings.largest_output_requests)}
        ${this.renderToolActivity(e.tool_activity)}
        ${this.renderInspectionTimeline(e.timeline,e.bounds.chronology_omitted??0)}
        ${this.renderInspectionArtifacts(e)}
        ${this.renderUnknownFacts(e)}
      </div>
    `}createAnalysis(){this.dispatchEvent(new CustomEvent("analysis-create",{bubbles:!0,composed:!0}))}renderAnalysis(){if(this.analysisLoading&&!this.analysis)return o`<div class="scroll"><p class="inspection-note">Starting analysis…</p></div>`;if(this.analysisError&&!this.analysis)return o`<div class="scroll">
        <p class="error-line">${this.analysisError}</p>
        <button class="analysis-action" @click=${()=>this.createAnalysis()}>Retry analysis</button>
      </div>`;const e=this.analysis;return!e||e.state==="not_started"?o`<div class="scroll">
        <h3>Run Analysis</h3>
        <p class="inspection-note">
          The Agent receives only bounded deterministic inspection facts. It does not browse, use a shell, or modify the subject run.
        </p>
        <button class="analysis-action" ?disabled=${this.analysisLoading} @click=${()=>this.createAnalysis()}>
          ${this.analysisLoading?"Starting…":"Create analysis.md"}
        </button>
      </div>`:e.state==="running"?o`<div class="scroll">
        <h3>Run Analysis</h3>
        <p class="inspection-note">Analysis Agent is inspecting the subject run…</p>
        <dl>
          <dt>Analysis run</dt><dd>${e.analysis_run_id??"Unknown"}</dd>
          <dt>Artifact</dt><dd>${e.artifact_path??"Unknown"}</dd>
        </dl>
      </div>`:e.state==="failed"?o`<div class="scroll">
        <h3>Run Analysis</h3>
        <p class="error-line">${e.error??"Analysis run failed."}</p>
        <dl>
          <dt>Analysis run</dt><dd>${e.analysis_run_id??"Unknown"}</dd>
          <dt>Artifact</dt><dd>${e.artifact_path??"Unknown"}</dd>
        </dl>
        <button class="analysis-action" @click=${()=>this.createAnalysis()}>Retry analysis</button>
      </div>`:o`<div class="scroll">
      <h3>Run Analysis</h3>
      <p class="inspection-note">
        Semantic diagnosis is stored as a human/Agent work artifact. Runtime facts remain in Inspection.
      </p>
      <dl>
        <dt>Analysis run</dt><dd>${e.analysis_run_id??"Unknown"}</dd>
        <dt>Artifact</dt><dd>${e.artifact_path??"Unknown"}</dd>
      </dl>
      ${e.content?o`<pre class="analysis-output">${e.content}</pre>`:o`<p class="inspection-note">analysis.md has no readable content.</p>`}
    </div>`}renderRequestRanking(e,t){return o`
      <h4>${e}</h4>
      ${t.length===0?o`<p class="inspection-note">No authoritative values available.</p>`:o`<table class="inspection-table">
            <thead><tr><th>Request</th><th class="number">Latency</th><th class="number">Input</th><th class="number">Output</th><th>Status</th></tr></thead>
            <tbody>${t.map(s=>o`<tr>
              <td>${s.request}</td>
              <td class="number ${s.latency_ms===null?"unknown":""}">${this.durationValue(s.latency_ms)}</td>
              <td class="number ${s.input_tokens===null?"unknown":""}">${this.tokenValue(s.input_tokens)}</td>
              <td class="number ${s.output_tokens===null?"unknown":""}">${this.tokenValue(s.output_tokens)}</td>
              <td>${s.status??"Unknown"}</td>
            </tr>`)}</tbody>
          </table>`}
    `}renderToolActivity(e){return o`
      <h4>Tool activity</h4>
      ${e.length===0?o`<p class="inspection-note">No tool calls recorded.</p>`:o`<table class="inspection-table">
            <thead><tr><th>Tool</th><th class="number">Total</th><th>Contiguous groups</th></tr></thead>
            <tbody>${e.map(t=>o`<tr>
              <td>${t.tool}</td>
              <td class="number">${t.total}</td>
              <td>${t.contiguous_groups.join(", ")||"None"}</td>
            </tr>`)}</tbody>
          </table>`}
    `}renderInspectionTimeline(e,t){return o`
      <h4>Observed sequence</h4>
      ${e.length===0?o`<p class="inspection-note">No bounded timeline facts available.</p>`:o`<table class="inspection-table">
            <thead><tr><th>Step</th><th>Kind</th><th>Title</th><th>Duration</th><th>Status</th></tr></thead>
            <tbody>${e.map(s=>o`<tr>
              <td>${s.step??"?"}</td>
              <td>${s.kind??"Unknown"}</td>
              <td>${s.title??"Unknown"}</td>
              <td>${this.durationValue(s.duration_ms)}</td>
              <td>${s.status??"Unknown"}</td>
            </tr>`)}</tbody>
          </table>`}
      ${t>0?o`<p class="inspection-note">${t.toLocaleString()} chronology row(s) omitted by the bounded view.</p>`:d}
    `}renderInspectionArtifacts(e){return o`
      <h4>Artifacts</h4>
      ${e.artifacts.length===0?o`<p class="inspection-note">No artifact facts recorded.</p>`:o`<ul class="inspection-list">${e.artifacts.map(t=>o`<li>
            ${t.path}${t.size!==null?` — ${ht(t.size)}`:""}
            ${t.change?` (${t.change})`:""}
          </li>`)}</ul>`}
    `}renderUnknownFacts(e){const t=e.unknown_facts,s=[...t.incomplete_requests,...t.unresolved_tool_calls,...t.started_tool_calls];return s.length>0||t.unavailable_usage.length>0||t.diagnostics.length>0?o`
      <h4>Unknown facts</h4>
      ${t.unavailable_usage.length>0?o`<p class="inspection-note">Unavailable: ${t.unavailable_usage.join(", ")}</p>`:d}
      ${s.length>0?o`<pre>${JSON.stringify(s,null,2)}</pre>`:d}
      ${t.diagnostics.map(i=>o`<p class="diag">${i}</p>`)}
    `:d}knownNumber(e){return e===null?"Unknown":e.toLocaleString()}durationValue(e){return e===null?"Unknown":A(e)}tokenValue(e){return e===null?"Unknown":j(e)}renderEvent(e,t){switch(e){case"io":return this.renderIo(t);case"usage":return this.renderUsage(t);case"raw":return this.renderRaw(t);default:return this.renderSummary(t)}}renderSummary(e){const s=(e.payload.events??[]).find(n=>n.tool_call_id)?.tool_call_id;return o`
      <h3>${e.title}</h3>
      <dl>
        <dt>Status</dt>
        <dd><zuaef-status-badge .status=${e.status??""}></zuaef-status-badge></dd>
        <dt>Kind</dt>
        <dd>${e.kind}</dd>
        ${e.step_index!==null?o`<dt>Step</dt><dd>#${e.step_index}</dd>`:d}
        <dt>Started</dt>
        <dd class=${e.started_at?"":"none"}>${e.started_at??"Unknown"}</dd>
        <dt>Finished</dt>
        <dd class=${e.finished_at?"":"none"}>${e.finished_at??"Unknown"}</dd>
        <dt>Duration</dt>
        <dd class=${e.duration_ms!==null?"":"none"}>
          ${e.duration_ms!==null?A(e.duration_ms):"Not derivable"}
        </dd>
        ${s?o`<dt>tool_call_id</dt><dd>${String(s)}</dd>`:d}
        ${e.detail?o`<dt>Error</dt><dd class="error-line">${e.detail}</dd>`:d}
        <dt>Derived from</dt>
        <dd>${e.source.join(", ")}</dd>
      </dl>
      ${this.renderEventPayloadHint(e)}
    `}renderEventPayloadHint(e){if(e.kind==="model_request"){const t=(e.payload.response_parts??[]).length>0;return o`<h4>Persisted data</h4>
        <p class="muted">
          ${t?"Per-response output parts are persisted (see Input/Output).":"No response message persisted for this request."}
        </p>`}if(e.kind==="tool_call"){const t=e.detail;return o`<h4>Persisted data</h4>
        <p class="muted">
          ${t?`Effect ledger: ${t}`:"No effect summary recorded."}
          Raw lifecycle events are under Raw.
        </p>`}return d}renderIo(e){const t=e.payload.response_parts??[];return t.length===0?o`<p class="muted">Not persisted</p>`:o`${t.map((s,n)=>this.renderPart(s,n))}`}renderPart(e,t){const s=typeof e.content=="string"?e.content:null;return o`
      <div class="part">
        <h4>Response part #${t} · ${e.part_kind}</h4>
        ${e.tool_name?o`<dl><dt>Tool</dt><dd>${e.tool_name}</dd></dl>`:d}
        ${s!==null?this.renderText(s,e.truncated===!0):d}
        ${e.args?o`<details>
              <summary>args</summary>
              <pre>${JSON.stringify(e.args,null,2)}</pre>
            </details>`:d}
      </div>
    `}renderText(e,t){if(e.length<=Ut)return o`<pre>${e}</pre>`;const s=t||e.length>=nt?" (already truncated by the API)":"";return o`<pre>${e.slice(0,Ut)}…</pre>
    <details>
      <summary>Show full text (${e.length.toLocaleString()} chars)${s}</summary>
      <pre>${e}</pre>
    </details>`}renderUsage(e){const t=e.usage??{};return o`
      <h3>Usage</h3>
      <dl>
        <dt>Input tokens</dt>
        <dd class=${t.input_tokens!==void 0?"":"none"}>
          ${t.input_tokens!==void 0?t.input_tokens.toLocaleString():"Unknown"}
        </dd>
        <dt>Output tokens</dt>
        <dd class=${t.output_tokens!==void 0?"":"none"}>
          ${t.output_tokens!==void 0?t.output_tokens.toLocaleString():"Unknown"}
        </dd>
        ${typeof t.requests=="number"?o`<dt>Requests</dt><dd>${t.requests}</dd>`:d}
      </dl>
    `}renderRaw(e){const t=JSON.stringify(e.payload,null,2)??"{}";return o`
      <h3>Raw</h3>
      <p class="muted">Exactly what GET /api/runs returned for this row.</p>
      ${t.length>nt?o`<p class="muted">Preview truncated at ${nt.toLocaleString()} chars.</p>
            <pre>${t.slice(0,nt)}…</pre>`:o`<pre>${t}</pre>`}
    `}renderRunOverview(){const e=this.projection;if(!e)return o`<p class="muted">Select a run.</p>`;const t=e.run,s=e.composition;return o`
      <h3>${t.display_label}</h3>
      <dl>
        <dt>Status</dt>
        <dd><zuaef-status-badge .status=${t.status}></zuaef-status-badge></dd>
        <dt>Run ID</dt>
        <dd>${t.run_id}</dd>
        ${t.conversation_id?o`<dt>Conversation</dt><dd>${t.conversation_id}</dd>`:d}
        ${t.parent_run_id?o`<dt>Parent run</dt><dd>${t.parent_run_id}</dd>`:d}
        ${t.continued_from_run_id?o`<dt>Continued from</dt><dd>${t.continued_from_run_id}</dd>`:d}
        <dt>Model</dt>
        <dd class=${t.model?"":"none"}>${t.model??"Unknown"}</dd>
        <dt>Profile</dt>
        <dd class=${t.profile?"":"none"}>${t.profile??"Unknown"}</dd>
        ${t.agent_name?o`<dt>Agent</dt><dd>${t.agent_name}</dd>`:d}
        <dt>Started</dt>
        <dd class=${t.started_at?"":"none"}>${jt(t.started_at)||"Unknown"}</dd>
        <dt>Finished</dt>
        <dd class=${t.finished_at?"":"none"}>${jt(t.finished_at)||"Unknown"}</dd>
        <dt>Duration</dt>
        <dd class=${t.duration_ms!==null?"":"none"}>
          ${t.duration_ms!==null?A(t.duration_ms):"Not derivable"}
        </dd>
        <dt>Requests</dt>
        <dd>${t.request_count}</dd>
        <dt>Tool calls</dt>
        <dd>${t.tool_call_count}</dd>
      </dl>

      <h4>Usage</h4>
      ${e.usage?o`<dl>
            <dt>Input tokens</dt>
            <dd class=${e.usage.input_tokens!==void 0?"":"none"}>
              ${e.usage.input_tokens!==void 0?e.usage.input_tokens.toLocaleString():"Unknown"}
            </dd>
            <dt>Output tokens</dt>
            <dd class=${e.usage.output_tokens!==void 0?"":"none"}>
              ${e.usage.output_tokens!==void 0?e.usage.output_tokens.toLocaleString():"Unknown"}
            </dd>
            <dt>Basis</dt>
            <dd>${e.usage.source??"unknown"}</dd>
          </dl>`:o`<p class="muted">Not persisted</p>`}

      <h4>Composition</h4>
      ${s?o`<details>
            <summary>${s.profile??"composition recorded"}</summary>
            <pre>${JSON.stringify(s,null,2)}</pre>
          </details>`:o`<p class="muted">Receipt unavailable</p>`}

      ${e.pause?o`<h4>Pause</h4>
            <p class="muted">
              Paused with ${e.pause.pending_approvals.length} pending
              approval(s). Supervision actions are not part of this read-only build.
            </p>`:d}

      ${e.unresolved_effects.length>0?o`<h4>Unresolved effects</h4>
            <pre>${JSON.stringify(e.unresolved_effects,null,2)}</pre>`:d}

      ${e.diagnostics.length>0?o`<h4>Diagnostics</h4>
            ${e.diagnostics.map(n=>o`<p class="diag">${n}</p>`)}`:d}

      ${e.artifacts.length>0?o`<h4>Artifacts</h4>
            ${e.artifacts.map(n=>o`<p class="muted">
                ${n.path}${n.size!==null?` — ${ht(n.size)}`:""}
              </p>`)}`:d}
    `}};y.styles=k`
    :host {
      display: flex;
      flex-direction: column;
      min-height: 0;
      background: var(--z-surface);
      border-left: 1px solid var(--z-border);
    }
    .tabs {
      display: flex;
      border-bottom: 1px solid var(--z-border);
      flex-shrink: 0;
    }
    .view-tabs {
      display: flex;
      border-bottom: 1px solid var(--z-border);
      background: var(--z-bg);
      flex-shrink: 0;
    }
    .view-tabs button {
      padding: var(--z-space-2) var(--z-space-3);
      font-size: 12px;
      color: var(--z-text-muted);
      background: transparent;
      border: none;
      border-bottom: 1px solid transparent;
      margin-bottom: -1px;
      cursor: pointer;
    }
    .view-tabs button:hover { color: var(--z-text); }
    .view-tabs button:focus-visible {
      outline: 1px dashed var(--z-accent);
      outline-offset: -1px;
    }
    .view-tabs button[aria-selected="true"] {
      color: var(--z-text);
      border-bottom-color: var(--z-accent);
    }
    .tabs button {
      padding: var(--z-space-2) var(--z-space-3);
      font-size: 12px;
      color: var(--z-text-muted);
      background: transparent;
      border: none;
      border-bottom: 1px solid transparent;
      margin-bottom: -1px;
      cursor: pointer;
    }
    .tabs button:hover { color: var(--z-text); }
    .tabs button:focus-visible {
      outline: 1px dashed var(--z-accent);
      outline-offset: -1px;
    }
    .tabs button[aria-selected="true"] {
      color: var(--z-text);
      border-bottom-color: var(--z-accent);
    }
    .scroll {
      flex: 1;
      overflow-y: auto;
      min-height: 0;
      padding: var(--z-space-3);
    }
    h3 {
      margin: 0 0 var(--z-space-2);
      font-size: 13px;
    }
    h4 {
      margin: var(--z-space-4) 0 var(--z-space-1);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--z-text-subtle);
    }
    dl {
      display: grid;
      grid-template-columns: 110px minmax(0, 1fr);
      gap: 4px var(--z-space-2);
      margin: 0;
    }
    dt {
      color: var(--z-text-subtle);
      font-size: 11px;
      letter-spacing: 0.02em;
      padding-top: 1px;
    }
    dd {
      margin: 0;
      font-family: var(--z-font-mono);
      font-size: 12px;
      color: var(--z-text);
      overflow-wrap: anywhere;
    }
    dd.none { color: var(--z-text-subtle); }
    pre {
      margin: var(--z-space-2) 0;
      padding: var(--z-space-2);
      background: var(--z-bg);
      border: 1px solid var(--z-border);
      border-radius: var(--z-radius);
      font-size: 11px;
      overflow-x: auto;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      max-height: 420px;
      overflow-y: auto;
    }
    details summary {
      cursor: pointer;
      color: var(--z-accent);
      font-size: 12px;
      user-select: none;
    }
    .part {
      border-top: 1px solid var(--z-border);
      padding-top: var(--z-space-2);
      margin-top: var(--z-space-2);
    }
    .part:first-of-type { border-top: none; margin-top: 0; padding-top: 0; }
    .muted { color: var(--z-text-muted); font-size: 12px; }
    .diag {
      color: var(--z-warning);
      font-family: var(--z-font-mono);
      font-size: 11px;
      overflow-wrap: anywhere;
      margin: 2px 0;
    }
    .error-line { color: var(--z-danger); overflow-wrap: anywhere; }
    .inspection-table {
      width: 100%;
      border-collapse: collapse;
      font-family: var(--z-font-mono);
      font-size: 11px;
    }
    .inspection-table th,
    .inspection-table td {
      border-bottom: 1px solid var(--z-divider);
      padding: 5px 4px;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }
    .inspection-table th {
      color: var(--z-text-subtle);
      font-weight: 500;
    }
    .inspection-table td.number,
    .inspection-table th.number { text-align: right; }
    .inspection-table td.unknown { color: var(--z-text-subtle); }
    .inspection-list {
      margin: 0;
      padding-left: 18px;
      color: var(--z-text-muted);
      font-family: var(--z-font-mono);
      font-size: 11px;
    }
    .inspection-note {
      color: var(--z-text-muted);
      font-size: 12px;
      line-height: 1.45;
    }
    .analysis-action {
      border: 1px solid var(--z-border);
      border-radius: var(--z-radius);
      padding: var(--z-space-2) var(--z-space-3);
      color: var(--z-text);
      background: var(--z-bg);
      cursor: pointer;
      font-size: 12px;
    }
    .analysis-action:hover:not(:disabled) { background: var(--z-surface-hover); }
    .analysis-action:disabled { opacity: 0.55; cursor: default; }
    .analysis-output {
      max-height: none;
      white-space: pre-wrap;
      font-family: var(--z-font-mono);
      line-height: 1.45;
    }
  `;x([u({attribute:!1})],y.prototype,"projection",2);x([u({attribute:!1})],y.prototype,"inspection",2);x([u()],y.prototype,"inspectorView",2);x([u({attribute:!1})],y.prototype,"analysis",2);x([u()],y.prototype,"selectedEventId",2);x([u()],y.prototype,"inspectorTab",2);x([u()],y.prototype,"inspectionLoading",2);x([u()],y.prototype,"inspectionError",2);x([u()],y.prototype,"analysisLoading",2);x([u()],y.prototype,"analysisError",2);y=x([R("zuaef-inspector")],y);const je={summary:"Summary",io:"Input/Output",usage:"Usage",raw:"Raw"};var Ue=Object.defineProperty,Ne=Object.getOwnPropertyDescriptor,_t=(e,t,s,n)=>{for(var i=n>1?void 0:n?Ne(t,s):t,r=e.length-1,a;r>=0;r--)(a=e[r])&&(i=(n?a(t,s,i):a(i))||i);return n&&i&&Ue(t,s,i),i};let Q=class extends b{constructor(){super(...arguments),this.selected=!1}select(){this.dispatchEvent(new CustomEvent("run-selected",{detail:{runId:this.run.run_id},bubbles:!0,composed:!0}))}render(){const e=this.run,t=[e.model,e.profile].filter(Boolean).join(" · ");return o`
      <button
        role="option"
        aria-selected=${this.selected?"true":"false"}
        title=${`${e.display_label} — ${e.status} (${e.started_at??"unknown start"})`}
        @click=${this.select}
      >
        <span class="glyph ${e.status}" aria-hidden="true"
          >${Le(e.status)}</span
        >
        <span class="label">${e.display_label}</span>
        <span class="time">${$e(e.started_at)}</span>
        ${t?o`<span class="meta">${t}</span>`:o`<span class="meta">no model/profile recorded</span>`}
      </button>
    `}};Q.styles=k`
    button {
      display: grid;
      grid-template-columns: 14px minmax(0, 1fr) auto;
      gap: 2px var(--z-space-2);
      width: 100%;
      padding: 5px var(--z-space-3);
      text-align: left;
      background: transparent;
      border: none;
      color: inherit;
    }
    button:hover { background: var(--z-hover-tint); }
    button:focus-visible {
      outline: 1px dashed var(--z-accent);
      outline-offset: -1px;
    }
    button[aria-selected="true"] {
      background: var(--z-selected-surface);
      box-shadow: inset 2px 0 0 var(--z-accent);
    }
    .glyph {
      grid-row: 1 / 3;
      align-self: center;
      font-family: var(--z-font-mono);
      font-size: 11px;
    }
    .glyph.failed { color: var(--z-danger); }
    .glyph.paused, .glyph.limit_reached { color: var(--z-warning); }
    .glyph.incomplete, .glyph.started { color: var(--z-accent); }
    .glyph.completed { color: var(--z-text-subtle); }
    .label {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--z-text);
    }
    .meta {
      font-size: 11px;
      color: var(--z-text-subtle);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .time {
      grid-column: 3;
      grid-row: 1 / 3;
      align-self: center;
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-text-muted);
    }
  `;_t([u({attribute:!1})],Q.prototype,"run",2);_t([u({type:Boolean})],Q.prototype,"selected",2);Q=_t([R("zuaef-run-row")],Q);function Le(e){switch(e){case"completed":return"✓";case"failed":return"✗";case"paused":return"⏸";case"limit_reached":return"⏹";case"incomplete":case"started":return"●";default:return"?"}}var Me=Object.defineProperty,De=Object.getOwnPropertyDescriptor,G=(e,t,s,n)=>{for(var i=n>1?void 0:n?De(t,s):t,r=e.length-1,a;r>=0;r--)(a=e[r])&&(i=(n?a(t,s,i):a(i))||i);return n&&i&&Me(t,s,i),i};let P=class extends b{constructor(){super(...arguments),this.runs=[],this.selectedRunId="",this.nextCursor=null,this.loadingMore=!1,this.filter=""}onFilter(e){this.dispatchEvent(new CustomEvent("run-filter",{detail:{value:e.target.value},bubbles:!0,composed:!0}))}passesFilter(e){return this.filter===""?!0:qe(e,this.filter)}render(){const e=this.runs.filter(i=>this.passesFilter(i)),t=[["Today",[]],["Yesterday",[]],["Older",[]]];for(const i of e)t[["Today","Yesterday","Older"].indexOf(ye(i))][1].push(i);const s=e.length,n=this.runs.length;return o`
      <div class="filter">
        <input
          type="search"
          placeholder="Filter runs…"
          .value=${this.filter}
          @input=${this.onFilter}
          aria-label="Filter runs"
        />
      </div>
      <div class="scroll" role="listbox" aria-label="Runs">
        ${n===0?o`<div class="state">Loading runs…</div>`:s===0?o`<div class="state">No runs match this filter.</div>`:t.map(([i,r])=>r.length>0?o`
                        <div class="group">${i}</div>
                        ${r.map(a=>o`
                            <zuaef-run-row
                              role="option"
                              .run=${a}
                              ?selected=${a.run_id===this.selectedRunId}
                            ></zuaef-run-row>
                          `)}
                      `:"")}
      </div>
      ${this.nextCursor?o`<button
            class="more"
            ?disabled=${this.loadingMore}
            @click=${()=>this.dispatchEvent(new CustomEvent("load-more",{bubbles:!0,composed:!0}))}
          >
            ${this.loadingMore?"Loading…":`Load more (${s} of ${n}+ loaded)`}
          </button>`:o`<div class="count">${s}${s<n?` of ${n}`:""} runs</div>`}
    `}};P.styles=k`
    :host {
      display: flex;
      flex-direction: column;
      min-height: 0;
      background: var(--z-surface);
      border-right: 1px solid var(--z-border);
    }
    .filter {
      padding: var(--z-space-2) var(--z-space-3);
      border-bottom: 1px solid var(--z-border);
    }
    input {
      width: 100%;
      background: var(--z-bg);
      border: 1px solid var(--z-border);
      border-radius: var(--z-radius);
      padding: 3px var(--z-space-2);
      color: var(--z-text);
      font-family: var(--z-font-mono);
      font-size: 12px;
    }
    .scroll {
      flex: 1;
      overflow-y: auto;
      min-height: 0;
    }
    .group {
      padding: var(--z-space-2) var(--z-space-3) var(--z-space-1);
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--z-text-subtle);
    }
    .more,
    .state {
      display: block;
      width: 100%;
      padding: var(--z-space-2) var(--z-space-3);
      border: none;
      border-top: 1px solid var(--z-border);
      background: transparent;
      color: var(--z-text-muted);
      font-size: 12px;
      text-align: left;
    }
    button.more:hover { background: var(--z-surface-hover); color: var(--z-text); }
    .count {
      padding: var(--z-space-1) var(--z-space-3);
      border-top: 1px solid var(--z-border);
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-text-subtle);
    }
  `;G([u({attribute:!1})],P.prototype,"runs",2);G([u()],P.prototype,"selectedRunId",2);G([u({attribute:!1})],P.prototype,"nextCursor",2);G([u({type:Boolean})],P.prototype,"loadingMore",2);G([u()],P.prototype,"filter",2);P=G([R("zuaef-run-list")],P);function qe(e,t){return[e.display_label,e.run_id,e.model,e.profile,e.status].filter(Boolean).join(`
`).toLowerCase().includes(t.toLowerCase())}var Ve=Object.defineProperty,He=Object.getOwnPropertyDescriptor,xt=(e,t,s,n)=>{for(var i=n>1?void 0:n?He(t,s):t,r=e.length-1,a;r>=0;r--)(a=e[r])&&(i=(n?a(t,s,i):a(i))||i);return n&&i&&Ve(t,s,i),i};const Ge={run:"RUN",model_request:"REQ",tool_call:"TOOL"};let tt=class extends b{constructor(){super(...arguments),this.selected=!1}select(){this.dispatchEvent(new CustomEvent("event-selected",{detail:{rowId:this.row.id},bubbles:!0,composed:!0}))}render(){const e=this.row,t=e.kind==="run",s=Ge[e.kind]??"EVENT",n=e.kind==="tool_call"?"tool":t?"run":"request";return o`
      <button
        role="option"
        aria-selected=${this.selected?"true":"false"}
        class=${[n,e.status?`state-${e.status}`:""].join(" ")}
        title=${e.title}
        @click=${this.select}
      >
        <span class="time">${q(e.started_at)}</span>
        <span class="kind">${t?"":s}</span>
        <span class="step">${e.step_index!==null?`#${e.step_index}`:""}</span>
        <span class="summary"
          >${e.title}${e.detail?o` <span class="detail">— ${e.detail}</span>`:""}</span
        >
        <span class="dur">${A(e.duration_ms)}</span>
        <span class="usage">${be(e.usage)}</span>
        <span class="status ${e.status??""}"
          >${e.status?`${Gt(e.status)} ${e.status}`:""}</span
        >
      </button>
    `}};tt.styles=k`
    button {
      display: grid;
      grid-template-columns:
        66px 44px 34px minmax(0, 1fr) 62px 110px 96px;
      gap: var(--z-space-3);
      align-items: baseline;
      width: 100%;
      padding: 2px var(--z-space-3);
      font-family: var(--z-font-mono);
      font-size: 12px;
      text-align: left;
      background: transparent;
      border: none;
      border-bottom: 1px solid var(--z-divider);
      white-space: nowrap;
      color: inherit;
    }
    button:hover { background: var(--z-hover-tint); }
    button:focus-visible {
      outline: 1px dashed var(--z-accent);
      outline-offset: -1px;
    }
    button[aria-selected="true"] {
      background: var(--z-selected-surface);
      box-shadow: inset 2px 0 0 var(--z-accent);
    }
    /* Anomalies are the loudest element on the ledger. */
    button.state-failed { background: var(--z-danger-tint); }
    button.state-unresolved { background: var(--z-warning-tint); }
    button.state-paused { background: var(--z-warning-tint); }

    .time { color: var(--z-text-subtle); }
    .kind {
      color: var(--z-text-subtle);
      letter-spacing: 0.04em;
      font-size: 11px;
    }
    .step { color: var(--z-text-subtle); }
    .summary {
      overflow: hidden;
      text-overflow: ellipsis;
      color: var(--z-text);
    }
    .summary .detail { color: var(--z-text-muted); }
    .dur, .usage {
      color: var(--z-text-muted);
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .status { text-align: right; color: var(--z-text-subtle); }
    .status.failed { color: var(--z-danger); }
    .status.paused, .status.limit_reached { color: var(--z-warning); }
    .status.incomplete, .status.started { color: var(--z-accent); }
    .status.unresolved, .status.unknown { color: var(--z-warning); }

    /* Secondary layer: tool rows are indented and muted inside their own
       summary cell so the shared ledger columns stay aligned. */
    button.tool .summary,
    button.tool .kind {
      padding-left: 14px;
      color: var(--z-text-muted);
    }
    /* Model requests carry the skeleton: slightly more breathing room. */
    button.request { margin-top: 4px; }
    button.run { margin-top: 2px; margin-bottom: 2px; }
  `;xt([u({attribute:!1})],tt.prototype,"row",2);xt([u({type:Boolean})],tt.prototype,"selected",2);tt=xt([R("zuaef-event-row")],tt);var Fe=Object.defineProperty,Be=Object.getOwnPropertyDescriptor,st=(e,t,s,n)=>{for(var i=n>1?void 0:n?Be(t,s):t,r=e.length-1,a;r>=0;r--)(a=e[r])&&(i=(n?a(t,s,i):a(i))||i);return n&&i&&Fe(t,s,i),i};const We=[{id:"latency",label:"Latency"},{id:"input",label:"Input tokens"},{id:"output",label:"Output tokens"}];let N=class extends b{constructor(){super(...arguments),this.timeline=[],this.selectedEventId="",this.metric="latency",this.now=Date.now(),this.ticker=null}updated(e){super.updated(e);const t=this.timeline.some(s=>ut(s));t&&this.ticker===null?this.ticker=setInterval(()=>{this.now=Date.now()},1e3):!t&&this.ticker!==null&&(clearInterval(this.ticker),this.ticker=null)}disconnectedCallback(){super.disconnectedCallback(),this.ticker!==null&&clearInterval(this.ticker),this.ticker=null}select(e){this.dispatchEvent(new CustomEvent("event-selected",{detail:{rowId:e},bubbles:!0,composed:!0}))}elapsedMs(e){const t=Date.parse(e.started_at??"");return Number.isNaN(t)?null:Math.max(this.now-t,0)}tipLines(e){const t=e.row,s=[o`<div>${t.title}</div>`,o`<div class="muted">${q(t.started_at)}</div>`];if(e.active){const n=this.elapsedMs(t);s.push(o`<div class="muted">
          elapsed ${n===null?"Unknown":A(n)}
        </div>`)}else s.push(o`<div class="muted">
          latency ${t.duration_ms===null?"Unknown":A(t.duration_ms)}
        </div>`);return s.push(o`<div class="muted">
        in ${t.usage?.input_tokens===void 0?"Unknown":j(t.usage.input_tokens)}
      </div>`,o`<div class="muted">
        out ${t.usage?.output_tokens===void 0?"Unknown":j(t.usage.output_tokens)}
      </div>`),t.status&&t.status!=="completed"&&s.push(o`<div class="muted">${Gt(t.status)} ${t.status}</div>`),s}render(){const e=Re(this.timeline,this.metric,this.now);if(e.bars.length===0)return"";const t=e.bars.find(s=>s.active);return o`
      <div class="head">
        <span class="label">OVERVIEW</span>
        ${We.map(s=>o`<button
            class="metric"
            aria-pressed=${this.metric===s.id?"true":"false"}
            @click=${()=>{this.metric=s.id}}
          >
            ${s.label}
          </button>`)}
        <span class="spacer"></span>
        ${t?o`<span class="active-note">
              ${t.row.title} running ·
              ${(()=>{const s=this.elapsedMs(t.row);return s===null?"Unknown":A(s)})()}
              elapsed
            </span>`:""}
      </div>
      <div class="plot" role="group" aria-label="Request overview minimap">
        ${e.ticks.map(s=>o`<span
            class=${["tick",s.row.id===this.selectedEventId?"selected":"",s.row.status?`state-${s.row.status}`:""].join(" ")}
            style="left: ${(s.x*100).toFixed(3)}%"
            title=${s.row.title}
          ></span>`)}
        ${e.bars.map(s=>{const n=s.row.id===this.selectedEventId,i=s.value===null?"Unknown":s.active&&this.metric==="latency"?`elapsed ${A(s.value)}`:String(s.value),r=["bar",s.active?"active":"",s.value===null?"unknown":"",s.row.status&&!s.active?`state-${s.row.status}`:""].join(" ");return o`<button
            class=${r}
            role="option"
            aria-selected=${n?"true":"false"}
            aria-label=${`${s.row.title} at ${q(s.row.started_at)}; ${this.metric} ${i}`}
            style=${`left: ${(s.x*100).toFixed(3)}%; height: ${(s.h*100).toFixed(1)}%`}
            title=${s.row.title}
            @click=${()=>this.select(s.row.id)}
          >
            <span class="tip">${this.tipLines(s)}</span>
          </button>`})}
        ${t?o`<span
              class="nowline"
              style="left: 100%"
              title="now"
            ></span>`:""}
      </div>
      <div class="axis">
        <span>${q(new Date(e.t0).toISOString())}</span>
        <span>${t?"NOW":q(new Date(e.t1).toISOString())}</span>
      </div>
    `}};N.styles=k`
    :host {
      display: block;
      border-bottom: 1px solid var(--z-border);
      padding: var(--z-space-2) var(--z-space-3) var(--z-space-1);
    }
    .head {
      display: flex;
      align-items: baseline;
      gap: var(--z-space-3);
      margin-bottom: var(--z-space-1);
    }
    .label {
      font-size: 10px;
      letter-spacing: 0.08em;
      color: var(--z-text-subtle);
    }
    .metric {
      padding: 0 var(--z-space-2);
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-text-muted);
      background: transparent;
      border: none;
      border-bottom: 1px solid transparent;
      cursor: pointer;
    }
    .metric:hover { color: var(--z-text); }
    .metric[aria-pressed="true"] {
      color: var(--z-text);
      border-bottom-color: var(--z-accent);
    }
    .metric:focus-visible {
      outline: 1px dashed var(--z-accent);
      outline-offset: -1px;
    }
    .spacer { flex: 1; }
    .active-note {
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-accent);
    }
    .unknown { border-style: dashed; opacity: 0.75; }
    .plot {
      position: relative;
      height: 64px;
      border-bottom: 1px solid var(--z-border);
    }
    .bar {
      position: absolute;
      bottom: 0;
      width: 8px;
      min-height: 3px;
      transform: translateX(-50%);
      background: var(--z-text-subtle);
      border: none;
      padding: 0;
      cursor: pointer;
    }
    .bar:hover { background: var(--z-text-muted); }
    .bar:focus-visible {
      outline: 1px dashed var(--z-accent);
      outline-offset: 1px;
    }
    .bar[aria-selected="true"] { background: var(--z-accent); }
    .bar.state-failed { background: var(--z-danger); }
    /* Running request: outlined hatch — visibly "not settled yet". */
    .bar.active {
      background: repeating-linear-gradient(
        45deg,
        transparent,
        transparent 2px,
        var(--z-accent) 2px,
        var(--z-accent) 3px
      );
      border: 1px solid var(--z-accent);
    }
    .tick {
      position: absolute;
      bottom: 0;
      width: 2px;
      height: 5px;
      transform: translateX(-50%);
      background: var(--z-text-subtle);
      opacity: 0.7;
    }
    .tick.selected { background: var(--z-accent); opacity: 1; }
    .tick.state-failed { background: var(--z-danger); }
    .nowline {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 1px;
      background: var(--z-warning);
      opacity: 0.6;
    }
    .axis {
      display: flex;
      justify-content: space-between;
      font-family: var(--z-font-mono);
      font-size: 10px;
      color: var(--z-text-subtle);
      padding-top: 2px;
    }
    /* CSS-only tooltip: facts on hover/focus, no floating layer. */
    .tip {
      display: none;
      position: absolute;
      bottom: calc(100% + 6px);
      left: 50%;
      transform: translateX(-50%);
      z-index: 1;
      white-space: nowrap;
      text-align: left;
      font-family: var(--z-font-mono);
      font-size: 11px;
      line-height: 1.5;
      color: var(--z-text);
      background: var(--z-surface);
      border: 1px solid var(--z-border);
      border-radius: var(--z-radius);
      padding: var(--z-space-1) var(--z-space-2);
      pointer-events: none;
    }
    .tip .muted { color: var(--z-text-muted); }
    .bar:hover .tip,
    .bar:focus-visible .tip { display: block; }
  `;st([u({attribute:!1})],N.prototype,"timeline",2);st([u()],N.prototype,"selectedEventId",2);st([g()],N.prototype,"metric",2);st([g()],N.prototype,"now",2);N=st([R("zuaef-overview-strip")],N);var Ze=Object.defineProperty,Je=Object.getOwnPropertyDescriptor,F=(e,t,s,n)=>{for(var i=n>1?void 0:n?Je(t,s):t,r=e.length-1,a;r>=0;r--)(a=e[r])&&(i=(n?a(t,s,i):a(i))||i);return n&&i&&Ze(t,s,i),i};let T=class extends b{constructor(){super(...arguments),this.projection=null,this.loading=!1,this.selectedEventId="",this.error="",this.expandedGroups=[],this.lastRunId=null}updated(e){super.updated(e),(e.has("selectedEventId")||e.has("projection"))&&this.scrollToSelected()}scrollToSelected(){const e=this.selectedEventId;if(e){for(const t of this.renderRoot.querySelectorAll("zuaef-event-row"))if(t.row?.id===e){t.scrollIntoView({block:"nearest",behavior:"smooth"});return}}}toggleGroup(e){this.expandedGroups=this.expandedGroups.includes(e)?this.expandedGroups.filter(t=>t!==e):[...this.expandedGroups,e]}isOpen(e){return this.expandedGroups.includes(e.groupId)||ze(e,this.selectedEventId)}groupTotal(e){const t=e.rows.reduce((s,n)=>n.duration_ms!==null?s+n.duration_ms:s,0);return t>0?A(t):""}renderEntry(e){if(!xe(e))return o`<zuaef-event-row
        role="option"
        .row=${e}
        ?selected=${e.id===this.selectedEventId}
        @event-selected=${i=>this.dispatchEvent(new CustomEvent("event-selected",{detail:i.detail,bubbles:!0,composed:!0}))}
      ></zuaef-event-row>`;const t=this.isOpen(e),s=e.rows[0],n=o`<button
      class="group-header"
      aria-expanded=${t?"true":"false"}
      title=${`${e.toolName} ×${e.rows.length} — click to ${t?"collapse":"expand"}`}
      @click=${()=>this.toggleGroup(e.groupId)}
    >
      <span class="time">${q(s.started_at)}</span>
      <span class="kind">TOOL</span>
      <span class="step"></span>
      <span class="summary"
        ><span class="caret" aria-hidden="true">${t?"▾":"▸"}</span
        >${e.toolName} ×${e.rows.length}</span
      >
      <span class="dur">${this.groupTotal(e)}</span>
      <span class="usage"></span>
      <span class="status">${e.rows.length} calls</span>
    </button>`;return t?o`${n}
      ${e.rows.map(i=>this.renderEntry(i))}`:n}render(){const e=this.projection?.run;return e&&e.run_id!==this.lastRunId&&(this.lastRunId=e.run_id,this.expandedGroups=[]),o`
      <header>
        <h2>${e?e.display_label:"Trajectory"}</h2>
        ${e?o`<zuaef-status-badge .status=${e.status}></zuaef-status-badge>`:""}
        ${e&&e.model?o`<span class="model">${e.model}</span>`:""}
      </header>
      ${this.projection?.diagnostics?.length?this.projection.diagnostics.map(t=>o`<div class="diag">${t}</div>`):""}
      ${this.projection&&!this.error?o`<zuaef-overview-strip
            .timeline=${this.projection.timeline}
            .selectedEventId=${this.selectedEventId}
            @event-selected=${t=>this.dispatchEvent(new CustomEvent("event-selected",{detail:t.detail,bubbles:!0,composed:!0}))}
          ></zuaef-overview-strip>`:""}
      <div class="scroll">
        ${this.error?o`<div class="state error">${this.error}</div>`:this.loading?o`<div class="state">Loading trajectory…</div>`:this.projection?this.projection.timeline.length===0?o`<div class="state">
                    No step events persisted for this run — only receipt-level facts exist.
                  </div>`:we(this.projection.timeline).map(t=>this.renderEntry(t)):o`<div class="state">Select a run to inspect its trajectory.</div>`}
      </div>
    `}};T.styles=k`
    :host {
      display: flex;
      flex-direction: column;
      min-height: 0;
    }
    header {
      display: flex;
      align-items: baseline;
      gap: var(--z-space-3);
      padding: var(--z-space-2) var(--z-space-3);
      border-bottom: 1px solid var(--z-border);
      min-width: 0;
    }
    h2 {
      margin: 0;
      font-size: 13px;
      font-weight: 600;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .model {
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-text-muted);
    }
    .diag {
      padding: var(--z-space-1) var(--z-space-3);
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-warning);
      border-bottom: 1px solid var(--z-border);
      overflow-wrap: anywhere;
    }
    .scroll {
      flex: 1;
      overflow-y: auto;
      min-height: 0;
      padding-top: var(--z-space-1);
    }
    .state {
      padding: var(--z-space-4) var(--z-space-3);
      color: var(--z-text-muted);
    }
    .error {
      color: var(--z-danger);
    }
    /* Group header shares the event-row ledger grid. */
    .group-header {
      display: grid;
      grid-template-columns:
        66px 44px 34px minmax(0, 1fr) 62px 110px 96px;
      gap: var(--z-space-3);
      align-items: baseline;
      width: 100%;
      padding: 2px var(--z-space-3);
      font-family: var(--z-font-mono);
      font-size: 12px;
      text-align: left;
      background: transparent;
      border: none;
      border-bottom: 1px solid var(--z-divider);
      color: inherit;
      white-space: nowrap;
    }
    .group-header:hover { background: var(--z-hover-tint); }
    .group-header:focus-visible {
      outline: 1px dashed var(--z-accent);
      outline-offset: -1px;
    }
    .group-header .time { color: var(--z-text-subtle); }
    .group-header .kind {
      color: var(--z-text-subtle);
      letter-spacing: 0.04em;
      font-size: 11px;
    }
    .group-header .summary {
      overflow: hidden;
      text-overflow: ellipsis;
      padding-left: 14px;
      color: var(--z-text-muted);
    }
    .group-header .caret {
      display: inline-block;
      width: 1.1em;
      color: var(--z-text-subtle);
    }
    .group-header .dur {
      color: var(--z-text-muted);
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .group-header .status {
      text-align: right;
      color: var(--z-text-subtle);
      font-size: 11px;
    }
  `;F([u({attribute:!1})],T.prototype,"projection",2);F([u({type:Boolean})],T.prototype,"loading",2);F([u()],T.prototype,"selectedEventId",2);F([u()],T.prototype,"error",2);F([g()],T.prototype,"expandedGroups",2);T=F([R("zuaef-trajectory-view")],T);var Ke=Object.defineProperty,Ye=Object.getOwnPropertyDescriptor,$=(e,t,s,n)=>{for(var i=n>1?void 0:n?Ye(t,s):t,r=e.length-1,a;r>=0;r--)(a=e[r])&&(i=(n?a(t,s,i):a(i))||i);return n&&i&&Ke(t,s,i),i};let m=class extends b{constructor(){super(...arguments),this.ui=ge,this.runs=[],this.nextCursor=null,this.loadingMore=!1,this.projection=null,this.projectionLoading=!1,this.projectionError="",this.inspection=null,this.inspectionLoading=!1,this.inspectionError="",this.analysis=null,this.analysisLoading=!1,this.analysisError="",this.live=!0,this.liveAvailable=!0,this.es=null,this.esRunId=void 0,this.invalidateTimer=null,this.analysisPollTimer=null,this.listRequestGeneration=0,this.projectionRequestGeneration=0}connectedCallback(){super.connectedCallback(),this.reloadRuns()}disconnectedCallback(){super.disconnectedCallback(),this.closeStream(),this.invalidateTimer!==null&&clearTimeout(this.invalidateTimer),this.analysisPollTimer!==null&&clearTimeout(this.analysisPollTimer)}willUpdate(e){if(super.willUpdate(e),e.has("ui")||e.has("live")||e.has("liveAvailable")){const t=e.get("ui");e.has("ui")&&(!t||t.selectedRunId!==this.ui.selectedRunId)&&this.ui.selectedRunId&&(this.live=!0),this.syncStream()}}closeStream(){this.es?.close(),this.es=null,this.esRunId=void 0,this.invalidateTimer!==null&&clearTimeout(this.invalidateTimer),this.invalidateTimer=null}syncStream(){const e=this.live&&this.liveAvailable?this.ui.selectedRunId:void 0;if(this.es&&this.esRunId===e||(this.closeStream(),!e))return;const t=new EventSource(O.runEventsUrl(e));this.es=t,this.esRunId=e,t.addEventListener("run_changed",()=>this.scheduleInvalidate(e)),t.onerror=()=>{this.es!==t||this.esRunId!==e||(this.liveAvailable=!1,this.live=!1,this.closeStream())}}scheduleInvalidate(e=this.esRunId){e&&(this.invalidateTimer!==null&&clearTimeout(this.invalidateTimer),this.invalidateTimer=setTimeout(()=>{this.invalidateTimer=null,!(!this.live||!this.liveAvailable||this.ui.selectedRunId!==e||this.esRunId!==e)&&(this.reloadProjection(e),this.ui.inspectorView==="inspection"&&this.reloadInspection(e),this.ui.inspectorView==="analysis"&&this.reloadAnalysis(e),this.reloadRuns())},150))}setLive(e){e&&!this.liveAvailable||(this.live=e,e&&this.ui.selectedRunId&&(this.reloadProjection(this.ui.selectedRunId),this.reloadRuns()))}async reloadRuns(){const e=++this.listRequestGeneration;this.loadingMore=!1;try{const t=await O.listRuns();if(e!==this.listRequestGeneration)return;this.runs=t.runs,this.nextCursor=t.next_cursor,!this.ui.selectedRunId&&this.runs.length>0&&this.selectRun(this.runs[0].run_id)}catch(t){if(e!==this.listRequestGeneration)return;this.projectionError=`Failed to load runs: ${M(t)}`}}async loadMore(e){const t=++this.listRequestGeneration;this.loadingMore=!0;try{const s=await O.listRuns(e);if(t!==this.listRequestGeneration)return;const n=new Set(this.runs.map(i=>i.run_id));this.runs=[...this.runs,...s.runs.filter(i=>!n.has(i.run_id))],this.nextCursor=s.next_cursor}catch(s){if(t!==this.listRequestGeneration)return;this.projectionError=`Failed to load more runs: ${M(s)}`}finally{t===this.listRequestGeneration&&(this.loadingMore=!1)}}async reloadProjection(e){const t=++this.projectionRequestGeneration,s=()=>t===this.projectionRequestGeneration&&this.ui.selectedRunId===e;this.projectionLoading=!this.projection||this.projection.run.run_id!==e,this.projectionLoading&&(this.projectionError="");try{const n=await O.getRun(e);if(!s())return;this.projection=n,this.projectionError="",document.title=`${this.projection.run.display_label} — ZUAEF Console`}catch(n){if(!s())return;this.projectionError=`Failed to load run: ${M(n)}`}finally{s()&&(this.projectionLoading=!1)}}async reloadInspection(e){this.inspectionLoading=!0,this.inspectionError="";try{const t=await O.getRunInspection(e);if(this.ui.selectedRunId!==e||this.ui.inspectorView!=="inspection")return;this.inspection=t}catch(t){if(this.ui.selectedRunId!==e||this.ui.inspectorView!=="inspection")return;this.inspection=null,this.inspectionError=`Failed to load inspection: ${M(t)}`}finally{this.ui.selectedRunId===e&&this.ui.inspectorView==="inspection"&&(this.inspectionLoading=!1)}}async reloadAnalysis(e){this.analysisPollTimer!==null&&(clearTimeout(this.analysisPollTimer),this.analysisPollTimer=null),this.analysisLoading=this.analysis===null,this.analysisError="";try{const t=await O.getRunAnalysis(e);if(this.ui.selectedRunId!==e||this.ui.inspectorView!=="analysis")return;this.analysis=t,t.state==="running"&&(this.analysisPollTimer=setTimeout(()=>{this.analysisPollTimer=null,this.reloadAnalysis(e)},750))}catch(t){if(this.ui.selectedRunId!==e||this.ui.inspectorView!=="analysis")return;this.analysis=null,this.analysisError=`Failed to load analysis: ${M(t)}`}finally{this.ui.selectedRunId===e&&this.ui.inspectorView==="analysis"&&(this.analysisLoading=!1)}}async createAnalysis(){const e=this.ui.selectedRunId;if(e){this.analysisLoading=!0,this.analysisError="";try{await O.createRunAnalysis(e,{selectedRowId:this.ui.selectedEventId??null}),await this.reloadAnalysis(e)}catch(t){this.ui.selectedRunId===e&&(this.analysisError=`Failed to create analysis: ${M(t)}`)}finally{this.ui.selectedRunId===e&&(this.analysisLoading=!1)}}}patchUi(e){this.ui={...this.ui,...e}}selectRun(e){if(this.liveAvailable=!0,this.live=!0,e===this.ui.selectedRunId){this.syncStream(),this.reloadProjection(e);return}this.inspection=null,this.inspectionError="",this.analysis=null,this.analysisError="",this.analysisPollTimer!==null&&clearTimeout(this.analysisPollTimer),this.patchUi({selectedRunId:e,selectedEventId:void 0}),this.syncStream(),this.reloadProjection(e)}selectInspectorView(e){e!==this.ui.inspectorView&&(this.patchUi({inspectorView:e}),e==="inspection"&&this.ui.selectedRunId&&this.reloadInspection(this.ui.selectedRunId),e==="analysis"&&this.ui.selectedRunId&&this.reloadAnalysis(this.ui.selectedRunId))}render(){const e=this.projection?.run??null,t=e?[e.model??"model unknown",e.profile??"profile unknown"].join(" · "):"";return o`
      <header class="topbar">
        <span class="brand">ZUAEF</span>
        <span class="meta">${t}</span>
        <span class="spacer"></span>
        <button
          class="live"
          aria-pressed=${this.live?"true":"false"}
          ?disabled=${!this.liveAvailable}
          title=${this.liveAvailable?this.live?"Live: refetches on server invalidation. Click to pause.":"Paused so you can inspect history. Click to resume (jump to now).":"Live updates unavailable — use Refresh."}
          @click=${()=>this.setLive(!this.live)}
        >
          ${this.live?"● LIVE":this.liveAvailable?"○ paused · jump to now":"○ live off"}
        </button>
        <button class="refresh" @click=${()=>{this.refresh()}}>
          Refresh
        </button>
      </header>
      <div class="panes">
        <zuaef-run-list
          .runs=${this.runs}
          .selectedRunId=${this.ui.selectedRunId??""}
          .nextCursor=${this.nextCursor}
          .loadingMore=${this.loadingMore}
          .filter=${this.ui.runFilter??""}
          @run-selected=${s=>this.selectRun(s.detail.runId)}
          @run-filter=${s=>this.patchUi({runFilter:s.detail.value})}
          @load-more=${()=>{this.nextCursor&&this.loadMore(this.nextCursor)}}
        ></zuaef-run-list>

        <zuaef-trajectory-view
          .projection=${this.projection}
          .loading=${this.projectionLoading}
          .selectedEventId=${this.ui.selectedEventId??""}
          .error=${this.projectionError}
          @event-selected=${s=>{this.patchUi({selectedEventId:s.detail.rowId}),this.setLive(!1)}}
        ></zuaef-trajectory-view>

        <zuaef-inspector
          .projection=${this.projection}
          .inspection=${this.inspection}
          .inspectionLoading=${this.inspectionLoading}
          .inspectionError=${this.inspectionError}
          .analysis=${this.analysis}
          .analysisLoading=${this.analysisLoading}
          .analysisError=${this.analysisError}
          .inspectorView=${this.ui.inspectorView}
          .selectedEventId=${this.ui.selectedEventId??""}
          .inspectorTab=${this.ui.inspectorTab}
          @view-selected=${s=>this.selectInspectorView(s.detail.view)}
          @tab-selected=${s=>this.patchUi({inspectorTab:s.detail.tab})}
          @analysis-create=${()=>{this.createAnalysis()}}
        ></zuaef-inspector>
      </div>
      <zuaef-artifact-bar
        .artifacts=${this.projection?.artifacts??[]}
        .pause=${this.projection?.pause??null}
      ></zuaef-artifact-bar>
    `}async refresh(){this.liveAvailable=!0,this.live=!0,this.syncStream();const e=this.ui.selectedRunId;await this.reloadRuns(),e&&this.ui.selectedRunId===e&&(await this.reloadProjection(e),this.ui.inspectorView==="inspection"&&await this.reloadInspection(e),this.ui.inspectorView==="analysis"&&await this.reloadAnalysis(e))}};m.styles=k`
    :host {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr) auto;
      height: 100vh;
    }
    .topbar {
      display: flex;
      align-items: center;
      gap: var(--z-space-4);
      padding: var(--z-space-2) var(--z-space-3);
      border-bottom: 1px solid var(--z-border);
      background: var(--z-surface);
    }
    .brand {
      font-weight: 700;
      letter-spacing: 0.12em;
      font-size: 13px;
    }
    .topbar .spacer { flex: 1; }
    .meta {
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-text-muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .refresh {
      border: 1px solid var(--z-border);
      border-radius: var(--z-radius);
      padding: 2px var(--z-space-2);
      color: var(--z-text-muted);
      font-size: 12px;
      background: transparent;
    }
    .refresh:hover { color: var(--z-text); background: var(--z-surface-hover); }
    .live {
      border: 1px solid var(--z-border);
      border-radius: var(--z-radius);
      padding: 2px var(--z-space-2);
      font-size: 12px;
      font-family: var(--z-font-mono);
      background: transparent;
      cursor: pointer;
    }
    .live[aria-pressed="true"] { color: var(--z-accent); }
    .live[aria-pressed="false"] { color: var(--z-text-muted); }
    .live:hover:not(:disabled) { color: var(--z-text); background: var(--z-surface-hover); }
    .live:disabled { opacity: 0.5; cursor: default; }
    .live:focus-visible {
      outline: 1px dashed var(--z-accent);
      outline-offset: 1px;
    }
    .panes {
      display: grid;
      grid-template-columns: 264px minmax(0, 1fr) 380px;
      min-height: 0;
    }
    @media (max-width: 1100px) {
      .panes { grid-template-columns: 220px minmax(0, 1fr) 320px; }
    }
  `;$([u({attribute:!1})],m.prototype,"ui",2);$([g()],m.prototype,"runs",2);$([g()],m.prototype,"nextCursor",2);$([g()],m.prototype,"loadingMore",2);$([g()],m.prototype,"projection",2);$([g()],m.prototype,"projectionLoading",2);$([g()],m.prototype,"projectionError",2);$([g()],m.prototype,"inspection",2);$([g()],m.prototype,"inspectionLoading",2);$([g()],m.prototype,"inspectionError",2);$([g()],m.prototype,"analysis",2);$([g()],m.prototype,"analysisLoading",2);$([g()],m.prototype,"analysisError",2);$([g()],m.prototype,"live",2);$([g()],m.prototype,"liveAvailable",2);m=$([R("zuaef-console")],m);function M(e){return e instanceof Error?e.message:String(e)}
