(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const i of document.querySelectorAll('link[rel="modulepreload"]'))r(i);new MutationObserver(i=>{for(const n of i)if(n.type==="childList")for(const o of n.addedNodes)o.tagName==="LINK"&&o.rel==="modulepreload"&&r(o)}).observe(document,{childList:!0,subtree:!0});function s(i){const n={};return i.integrity&&(n.integrity=i.integrity),i.referrerPolicy&&(n.referrerPolicy=i.referrerPolicy),i.crossOrigin==="use-credentials"?n.credentials="include":i.crossOrigin==="anonymous"?n.credentials="omit":n.credentials="same-origin",n}function r(i){if(i.ep)return;i.ep=!0;const n=s(i);fetch(i.href,n)}})();const Q=globalThis,ut=Q.ShadowRoot&&(Q.ShadyCSS===void 0||Q.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,pt=Symbol(),xt=new WeakMap;let It=class{constructor(t,s,r){if(this._$cssResult$=!0,r!==pt)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=s}get styleSheet(){let t=this.o;const s=this.t;if(ut&&t===void 0){const r=s!==void 0&&s.length===1;r&&(t=xt.get(s)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),r&&xt.set(s,t))}return t}toString(){return this.cssText}};const Ft=e=>new It(typeof e=="string"?e:e+"",void 0,pt),z=(e,...t)=>{const s=e.length===1?e[0]:t.reduce((r,i,n)=>r+(o=>{if(o._$cssResult$===!0)return o.cssText;if(typeof o=="number")return o;throw Error("Value passed to 'css' function must be a 'css' function result: "+o+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[n+1],e[0]);return new It(s,e,pt)},Gt=(e,t)=>{if(ut)e.adoptedStyleSheets=t.map(s=>s instanceof CSSStyleSheet?s:s.styleSheet);else for(const s of t){const r=document.createElement("style"),i=Q.litNonce;i!==void 0&&r.setAttribute("nonce",i),r.textContent=s.cssText,e.appendChild(r)}},yt=ut?e=>e:e=>e instanceof CSSStyleSheet?(t=>{let s="";for(const r of t.cssRules)s+=r.cssText;return Ft(s)})(e):e;const{is:Vt,defineProperty:Wt,getOwnPropertyDescriptor:Zt,getOwnPropertyNames:Kt,getOwnPropertySymbols:Jt,getPrototypeOf:Yt}=Object,nt=globalThis,zt=nt.trustedTypes,Xt=zt?zt.emptyScript:"",Qt=nt.reactiveElementPolyfillSupport,q=(e,t)=>e,et={toAttribute(e,t){switch(t){case Boolean:e=e?Xt:null;break;case Object:case Array:e=e==null?e:JSON.stringify(e)}return e},fromAttribute(e,t){let s=e;switch(t){case Boolean:s=e!==null;break;case Number:s=e===null?null:Number(e);break;case Object:case Array:try{s=JSON.parse(e)}catch{s=null}}return s}},ht=(e,t)=>!Vt(e,t),wt={attribute:!0,type:String,converter:et,reflect:!1,useDefault:!1,hasChanged:ht};Symbol.metadata??=Symbol("metadata"),nt.litPropertyMetadata??=new WeakMap;let T=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,s=wt){if(s.state&&(s.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((s=Object.create(s)).wrapped=!0),this.elementProperties.set(t,s),!s.noAccessor){const r=Symbol(),i=this.getPropertyDescriptor(t,r,s);i!==void 0&&Wt(this.prototype,t,i)}}static getPropertyDescriptor(t,s,r){const{get:i,set:n}=Zt(this.prototype,t)??{get(){return this[s]},set(o){this[s]=o}};return{get:i,set(o){const c=i?.call(this);n?.call(this,o),this.requestUpdate(t,c,r)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??wt}static _$Ei(){if(this.hasOwnProperty(q("elementProperties")))return;const t=Yt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(q("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(q("properties"))){const s=this.properties,r=[...Kt(s),...Jt(s)];for(const i of r)this.createProperty(i,s[i])}const t=this[Symbol.metadata];if(t!==null){const s=litPropertyMetadata.get(t);if(s!==void 0)for(const[r,i]of s)this.elementProperties.set(r,i)}this._$Eh=new Map;for(const[s,r]of this.elementProperties){const i=this._$Eu(s,r);i!==void 0&&this._$Eh.set(i,s)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const s=[];if(Array.isArray(t)){const r=new Set(t.flat(1/0).reverse());for(const i of r)s.unshift(yt(i))}else t!==void 0&&s.push(yt(t));return s}static _$Eu(t,s){const r=s.attribute;return r===!1?void 0:typeof r=="string"?r:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,s=this.constructor.elementProperties;for(const r of s.keys())this.hasOwnProperty(r)&&(t.set(r,this[r]),delete this[r]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Gt(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,s,r){this._$AK(t,r)}_$ET(t,s){const r=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,r);if(i!==void 0&&r.reflect===!0){const n=(r.converter?.toAttribute!==void 0?r.converter:et).toAttribute(s,r.type);this._$Em=t,n==null?this.removeAttribute(i):this.setAttribute(i,n),this._$Em=null}}_$AK(t,s){const r=this.constructor,i=r._$Eh.get(t);if(i!==void 0&&this._$Em!==i){const n=r.getPropertyOptions(i),o=typeof n.converter=="function"?{fromAttribute:n.converter}:n.converter?.fromAttribute!==void 0?n.converter:et;this._$Em=i;const c=o.fromAttribute(s,n.type);this[i]=c??this._$Ej?.get(i)??c,this._$Em=null}}requestUpdate(t,s,r,i=!1,n){if(t!==void 0){const o=this.constructor;if(i===!1&&(n=this[t]),r??=o.getPropertyOptions(t),!((r.hasChanged??ht)(n,s)||r.useDefault&&r.reflect&&n===this._$Ej?.get(t)&&!this.hasAttribute(o._$Eu(t,r))))return;this.C(t,s,r)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,s,{useDefault:r,reflect:i,wrapped:n},o){r&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,o??s??this[t]),n!==!0||o!==void 0)||(this._$AL.has(t)||(this.hasUpdated||r||(s=void 0),this._$AL.set(t,s)),i===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(s){Promise.reject(s)}const t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[i,n]of this._$Ep)this[i]=n;this._$Ep=void 0}const r=this.constructor.elementProperties;if(r.size>0)for(const[i,n]of r){const{wrapped:o}=n,c=this[i];o!==!0||this._$AL.has(i)||c===void 0||this.C(i,void 0,n,c)}}let t=!1;const s=this._$AL;try{t=this.shouldUpdate(s),t?(this.willUpdate(s),this._$EO?.forEach(r=>r.hostUpdate?.()),this.update(s)):this._$EM()}catch(r){throw t=!1,this._$EM(),r}t&&this._$AE(s)}willUpdate(t){}_$AE(t){this._$EO?.forEach(s=>s.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(s=>this._$ET(s,this[s])),this._$EM()}updated(t){}firstUpdated(t){}};T.elementStyles=[],T.shadowRootOptions={mode:"open"},T[q("elementProperties")]=new Map,T[q("finalized")]=new Map,Qt?.({ReactiveElement:T}),(nt.reactiveElementVersions??=[]).push("2.1.2");const ft=globalThis,Et=e=>e,st=ft.trustedTypes,At=st?st.createPolicy("lit-html",{createHTML:e=>e}):void 0,Ut="$lit$",A=`lit$${Math.random().toFixed(9).slice(2)}$`,Nt="?"+A,te=`<${Nt}>`,R=document,B=()=>R.createComment(""),F=e=>e===null||typeof e!="object"&&typeof e!="function",vt=Array.isArray,ee=e=>vt(e)||typeof e?.[Symbol.iterator]=="function",lt=`[ 	
\f\r]`,H=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,St=/-->/g,Pt=/>/g,O=RegExp(`>|${lt}(?:([^\\s"'>=/]+)(${lt}*=${lt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Ot=/'/g,Ct=/"/g,Mt=/^(?:script|style|textarea|title)$/i,se=e=>(t,...s)=>({_$litType$:e,strings:t,values:s}),a=se(1),U=Symbol.for("lit-noChange"),d=Symbol.for("lit-nothing"),kt=new WeakMap,C=R.createTreeWalker(R,129);function Dt(e,t){if(!vt(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return At!==void 0?At.createHTML(t):t}const re=(e,t)=>{const s=e.length-1,r=[];let i,n=t===2?"<svg>":t===3?"<math>":"",o=H;for(let c=0;c<s;c++){const l=e[c];let f,v,u=-1,g=0;for(;g<l.length&&(o.lastIndex=g,v=o.exec(l),v!==null);)g=o.lastIndex,o===H?v[1]==="!--"?o=St:v[1]!==void 0?o=Pt:v[2]!==void 0?(Mt.test(v[2])&&(i=RegExp("</"+v[2],"g")),o=O):v[3]!==void 0&&(o=O):o===O?v[0]===">"?(o=i??H,u=-1):v[1]===void 0?u=-2:(u=o.lastIndex-v[2].length,f=v[1],o=v[3]===void 0?O:v[3]==='"'?Ct:Ot):o===Ct||o===Ot?o=O:o===St||o===Pt?o=H:(o=O,i=void 0);const _=o===O&&e[c+1].startsWith("/>")?" ":"";n+=o===H?l+te:u>=0?(r.push(f),l.slice(0,u)+Ut+l.slice(u)+A+_):l+A+(u===-2?c:_)}return[Dt(e,n+(e[s]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),r]};class G{constructor({strings:t,_$litType$:s},r){let i;this.parts=[];let n=0,o=0;const c=t.length-1,l=this.parts,[f,v]=re(t,s);if(this.el=G.createElement(f,r),C.currentNode=this.el.content,s===2||s===3){const u=this.el.content.firstChild;u.replaceWith(...u.childNodes)}for(;(i=C.nextNode())!==null&&l.length<c;){if(i.nodeType===1){if(i.hasAttributes())for(const u of i.getAttributeNames())if(u.endsWith(Ut)){const g=v[o++],_=i.getAttribute(u).split(A),p=/([.?@])?(.*)/.exec(g);l.push({type:1,index:n,name:p[2],strings:_,ctor:p[1]==="."?ne:p[1]==="?"?oe:p[1]==="@"?ae:ot}),i.removeAttribute(u)}else u.startsWith(A)&&(l.push({type:6,index:n}),i.removeAttribute(u));if(Mt.test(i.tagName)){const u=i.textContent.split(A),g=u.length-1;if(g>0){i.textContent=st?st.emptyScript:"";for(let _=0;_<g;_++)i.append(u[_],B()),C.nextNode(),l.push({type:2,index:++n});i.append(u[g],B())}}}else if(i.nodeType===8)if(i.data===Nt)l.push({type:2,index:n});else{let u=-1;for(;(u=i.data.indexOf(A,u+1))!==-1;)l.push({type:7,index:n}),u+=A.length-1}n++}}static createElement(t,s){const r=R.createElement("template");return r.innerHTML=t,r}}function N(e,t,s=e,r){if(t===U)return t;let i=r!==void 0?s._$Co?.[r]:s._$Cl;const n=F(t)?void 0:t._$litDirective$;return i?.constructor!==n&&(i?._$AO?.(!1),n===void 0?i=void 0:(i=new n(e),i._$AT(e,s,r)),r!==void 0?(s._$Co??=[])[r]=i:s._$Cl=i),i!==void 0&&(t=N(e,i._$AS(e,t.values),i,r)),t}class ie{constructor(t,s){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=s}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:s},parts:r}=this._$AD,i=(t?.creationScope??R).importNode(s,!0);C.currentNode=i;let n=C.nextNode(),o=0,c=0,l=r[0];for(;l!==void 0;){if(o===l.index){let f;l.type===2?f=new K(n,n.nextSibling,this,t):l.type===1?f=new l.ctor(n,l.name,l.strings,this,t):l.type===6&&(f=new le(n,this,t)),this._$AV.push(f),l=r[++c]}o!==l?.index&&(n=C.nextNode(),o++)}return C.currentNode=R,i}p(t){let s=0;for(const r of this._$AV)r!==void 0&&(r.strings!==void 0?(r._$AI(t,r,s),s+=r.strings.length-2):r._$AI(t[s])),s++}}class K{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,s,r,i){this.type=2,this._$AH=d,this._$AN=void 0,this._$AA=t,this._$AB=s,this._$AM=r,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const s=this._$AM;return s!==void 0&&t?.nodeType===11&&(t=s.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,s=this){t=N(this,t,s),F(t)?t===d||t==null||t===""?(this._$AH!==d&&this._$AR(),this._$AH=d):t!==this._$AH&&t!==U&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):ee(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==d&&F(this._$AH)?this._$AA.nextSibling.data=t:this.T(R.createTextNode(t)),this._$AH=t}$(t){const{values:s,_$litType$:r}=t,i=typeof r=="number"?this._$AC(t):(r.el===void 0&&(r.el=G.createElement(Dt(r.h,r.h[0]),this.options)),r);if(this._$AH?._$AD===i)this._$AH.p(s);else{const n=new ie(i,this),o=n.u(this.options);n.p(s),this.T(o),this._$AH=n}}_$AC(t){let s=kt.get(t.strings);return s===void 0&&kt.set(t.strings,s=new G(t)),s}k(t){vt(this._$AH)||(this._$AH=[],this._$AR());const s=this._$AH;let r,i=0;for(const n of t)i===s.length?s.push(r=new K(this.O(B()),this.O(B()),this,this.options)):r=s[i],r._$AI(n),i++;i<s.length&&(this._$AR(r&&r._$AB.nextSibling,i),s.length=i)}_$AR(t=this._$AA.nextSibling,s){for(this._$AP?.(!1,!0,s);t!==this._$AB;){const r=Et(t).nextSibling;Et(t).remove(),t=r}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}}class ot{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,s,r,i,n){this.type=1,this._$AH=d,this._$AN=void 0,this.element=t,this.name=s,this._$AM=i,this.options=n,r.length>2||r[0]!==""||r[1]!==""?(this._$AH=Array(r.length-1).fill(new String),this.strings=r):this._$AH=d}_$AI(t,s=this,r,i){const n=this.strings;let o=!1;if(n===void 0)t=N(this,t,s,0),o=!F(t)||t!==this._$AH&&t!==U,o&&(this._$AH=t);else{const c=t;let l,f;for(t=n[0],l=0;l<n.length-1;l++)f=N(this,c[r+l],s,l),f===U&&(f=this._$AH[l]),o||=!F(f)||f!==this._$AH[l],f===d?t=d:t!==d&&(t+=(f??"")+n[l+1]),this._$AH[l]=f}o&&!i&&this.j(t)}j(t){t===d?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class ne extends ot{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===d?void 0:t}}class oe extends ot{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==d)}}class ae extends ot{constructor(t,s,r,i,n){super(t,s,r,i,n),this.type=5}_$AI(t,s=this){if((t=N(this,t,s,0)??d)===U)return;const r=this._$AH,i=t===d&&r!==d||t.capture!==r.capture||t.once!==r.once||t.passive!==r.passive,n=t!==d&&(r===d||i);i&&this.element.removeEventListener(this.name,this,r),n&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class le{constructor(t,s,r){this.element=t,this.type=6,this._$AN=void 0,this._$AM=s,this.options=r}get _$AU(){return this._$AM._$AU}_$AI(t){N(this,t)}}const de=ft.litHtmlPolyfillSupport;de?.(G,K),(ft.litHtmlVersions??=[]).push("3.3.3");const ce=(e,t,s)=>{const r=s?.renderBefore??t;let i=r._$litPart$;if(i===void 0){const n=s?.renderBefore??null;r._$litPart$=i=new K(t.insertBefore(B(),n),n,void 0,s??{})}return i._$AI(e),i};const mt=globalThis;class m extends T{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const s=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=ce(s,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return U}}m._$litElement$=!0,m.finalized=!0,mt.litElementHydrateSupport?.({LitElement:m});const ue=mt.litElementPolyfillSupport;ue?.({LitElement:m});(mt.litElementVersions??=[]).push("4.2.2");const w=e=>(t,s)=>{s!==void 0?s.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)};const pe={attribute:!0,type:String,converter:et,reflect:!1,hasChanged:ht},he=(e=pe,t,s)=>{const{kind:r,metadata:i}=s;let n=globalThis.litPropertyMetadata.get(i);if(n===void 0&&globalThis.litPropertyMetadata.set(i,n=new Map),r==="setter"&&((e=Object.create(e)).wrapped=!0),n.set(s.name,e),r==="accessor"){const{name:o}=s;return{set(c){const l=t.get.call(this);t.set.call(this,c),this.requestUpdate(o,l,e,!0,c)},init(c){return c!==void 0&&this.C(o,void 0,e,c),c}}}if(r==="setter"){const{name:o}=s;return function(c){const l=this[o];t.call(this,c),this.requestUpdate(o,l,e,!0,c)}}throw Error("Unsupported decorator location: "+r)};function h(e){return(t,s)=>typeof s=="object"?he(e,t,s):((r,i,n)=>{const o=i.hasOwnProperty(n);return i.constructor.createProperty(n,r),o?Object.getOwnPropertyDescriptor(i,n):void 0})(e,t,s)}function b(e){return h({...e,state:!0,attribute:!1})}class fe extends Error{constructor(t,s,r){super(s),this.code=t,this.status=r}}async function dt(e){const t=await fetch(e);if(!t.ok){let s="INTERNAL_ERROR",r=`HTTP ${t.status}`;try{const i=await t.json();i.error?.code&&(s=i.error.code),i.error?.message&&(r=i.error.message)}catch{}throw new fe(s,r,t.status)}return await t.json()}const Rt=200,Y={health:()=>dt("/api/health"),listRuns:e=>dt(e?`/api/runs?limit=${Rt}&cursor=${encodeURIComponent(e)}`:`/api/runs?limit=${Rt}`),getRun:e=>dt(`/api/runs/${encodeURIComponent(e)}`),runEventsUrl:e=>`/api/runs/${encodeURIComponent(e)}/events`},ve={inspectorTab:"summary"},tt=864e5;function I(e){if(!e)return"";const t=new Date(e);return Number.isNaN(t.getTime())?"":t.toLocaleTimeString(void 0,{hour12:!1})}function jt(e){if(!e)return"";const t=new Date(e);return Number.isNaN(t.getTime())?"":t.toLocaleString(void 0,{year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:!1})}function me(e,t=Date.now()){if(!e)return"—";const s=new Date(e);if(Number.isNaN(s.getTime()))return"—";const r=t-s.getTime();return r<6e4?"just now":r<36e5?`${Math.floor(r/6e4)}m ago`:r<tt?`${Math.floor(r/36e5)}h ago`:r<7*tt?`${Math.floor(r/tt)}d ago`:s.toLocaleDateString()}function k(e){if(e==null||e<0)return"";const t=e/1e3;if(t<60)return`${t.toFixed(1)}s`;const s=Math.floor(t/60),r=Math.round(t-s*60);return`${s}m${String(r).padStart(2,"0")}s`}function rt(e){return typeof e!="number"?"":e>=1e3?`${(e/1e3).toFixed(1)}k`:String(e)}function Lt(e){return e==null?"Unknown":e>=1048576?`${(e/1048576).toFixed(1)} MB`:e>=1024?`${(e/1024).toFixed(1)} KB`:`${e} B`}function $e(e){if(!e)return"";const t=[],s=rt(e.input_tokens),r=rt(e.output_tokens);return s&&t.push(`${s} in`),r&&t.push(`${r} out`),t.join(" · ")}function ge(e,t=Date.now()){if(!e.started_at)return"Older";const s=new Date(e.started_at).getTime();if(Number.isNaN(s))return"Older";const r=new Date(t).setHours(0,0,0,0);return s>=r?"Today":s>=r-tt?"Yesterday":"Older"}const Ht={completed:"✓",failed:"✗",paused:"⏸",incomplete:"◔",started:"●",unresolved:"?",unknown:"?",limit_reached:"⏹"};function qt(e){return e?Ht[e]??"·":""}function be(e,t){if(t)return e.find(s=>s.id===t)}function _e(e){return"groupId"in e}function xe(e){const t=[];let s=0;for(;s<e.length;){const r=e[s];if(r.kind!=="tool_call"){t.push(r),s+=1;continue}let i=s+1;for(;i<e.length&&e[i].kind==="tool_call"&&e[i].title===r.title;)i+=1;i-s>=2?t.push({groupId:`tool-group-${r.id}`,toolName:r.title,rows:e.slice(s,i)}):t.push(r),s=i}return t}function ye(e,t){return t?e.rows.some(s=>s.id===t):!1}const ze=200;function x(e){if(!e.started_at)return null;const t=Date.parse(e.started_at);return Number.isNaN(t)?null:t}function $t(e){return e.status==="started"||e.status==="incomplete"}function we(e){const t=x(e);if(t===null)return null;if(e.duration_ms!==null)return t+e.duration_ms;const s=e.finished_at?Date.parse(e.finished_at):NaN;return Number.isNaN(s)?t:s}function Ee(e,t,s){if(t==="input")return e.usage?.input_tokens??0;if(t==="output")return e.usage?.output_tokens??0;if(e.duration_ms!==null)return e.duration_ms;const r=x(e);return r===null||!$t(e)?0:Math.max(s-r,0)}function Ae(e,t,s){const i=e.filter(p=>p.kind==="model_request"&&x(p)!==null).sort((p,E)=>(x(p)??0)-(x(E)??0)).slice(-60);if(i.length===0)return{bars:[],ticks:[],t0:0,t1:0,span:0};let n=x(i[0])??0,o=Math.max(...i.map(p=>we(p)??x(p)??0));const c=p=>{const E=x(p);return p.kind==="tool_call"&&E!==null&&E>=n&&E<=o},l=e.filter(c).slice(0,ze).map(p=>({row:p,x:0})),f=Math.max(o-n,1),v=p=>Math.min(Math.max((p-n)/f,0),1),u=i.map(p=>Ee(p,t,s)),g=Math.max(...u,1),_=i.map((p,E)=>({row:p,x:v(x(p)??n),h:Math.max(Math.min(u[E]/g,1),.04),value:u[E],active:$t(p)}));for(const p of l)p.x=v(x(p.row)??n);return{bars:_,ticks:l,t0:n,t1:o,span:f}}var Se=Object.defineProperty,Pe=Object.getOwnPropertyDescriptor,gt=(e,t,s,r)=>{for(var i=r>1?void 0:r?Pe(t,s):t,n=e.length-1,o;n>=0;n--)(o=e[n])&&(i=(r?o(t,s,i):o(i))||i);return r&&i&&Se(t,s,i),i};let V=class extends m{constructor(){super(...arguments),this.artifacts=[],this.pause=null}render(){return a`
      <span class="label">Artifact</span>
      ${this.artifacts.length===0?a`<span class="none">No artifacts recorded for this run</span>`:this.artifacts.map(e=>a`<span class="artifact" title=${e.sha256}>
              <span class="path">${e.path}</span>
              <span class="fact">${Lt(e.size)}</span>
              <span class="fact">${e.change}</span>
              <span class="fact">sha256:${e.sha256.slice(0,12)}</span>
            </span>`)}
      ${this.pause?a`<span class="pause">
            ⏸ paused — ${this.pause.pending_approvals.length} approval(s) pending
            (supervision not wired in read-only build)
          </span>`:""}
    `}};V.styles=z`
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
  `;gt([h({attribute:!1})],V.prototype,"artifacts",2);gt([h({attribute:!1})],V.prototype,"pause",2);V=gt([w("zuaef-artifact-bar")],V);var Oe=Object.defineProperty,Ce=Object.getOwnPropertyDescriptor,Bt=(e,t,s,r)=>{for(var i=r>1?void 0:r?Ce(t,s):t,n=e.length-1,o;n>=0;n--)(o=e[n])&&(i=(r?o(t,s,i):o(i))||i);return r&&i&&Oe(t,s,i),i};let it=class extends m{constructor(){super(...arguments),this.status=""}render(){const e=this.status||"unknown";return a`<span class=${e}
      ><span aria-hidden="true">${Ht[e]??"·"}</span>${e}</span
    >`}};it.styles=z`
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
  `;Bt([h()],it.prototype,"status",2);it=Bt([w("zuaef-status-badge")],it);var ke=Object.defineProperty,Re=Object.getOwnPropertyDescriptor,at=(e,t,s,r)=>{for(var i=r>1?void 0:r?Re(t,s):t,n=e.length-1,o;n>=0;n--)(o=e[n])&&(i=(r?o(t,s,i):o(i))||i);return r&&i&&ke(t,s,i),i};const Tt=2e3,X=2e4;let M=class extends m{constructor(){super(...arguments),this.projection=null,this.selectedEventId="",this.inspectorTab="summary"}get row(){return be(this.projection?.timeline??[],this.selectedEventId)}get availableTabs(){const e=this.row;if(!e)return["summary"];const t=["summary"];return(e.payload.response_parts??[]).length>0&&t.push("io"),e.usage&&Object.keys(e.usage).length>0&&t.push("usage"),t.push("raw"),t}setTab(e){this.dispatchEvent(new CustomEvent("tab-selected",{detail:{tab:e},bubbles:!0,composed:!0}))}render(){const e=this.availableTabs,t=e.includes(this.inspectorTab)?this.inspectorTab:"summary",s=this.row;return a`
      ${e.length>1?a`<div class="tabs" role="tablist">
            ${e.map(r=>a`<button
                role="tab"
                aria-selected=${r===t?"true":"false"}
                @click=${()=>this.setTab(r)}
              >
                ${je[r]}
              </button>`)}
          </div>`:""}
      <div class="scroll">
        ${s?this.renderEvent(t,s):this.renderRunOverview()}
      </div>
    `}renderEvent(e,t){switch(e){case"io":return this.renderIo(t);case"usage":return this.renderUsage(t);case"raw":return this.renderRaw(t);default:return this.renderSummary(t)}}renderSummary(e){const s=(e.payload.events??[]).find(r=>r.tool_call_id)?.tool_call_id;return a`
      <h3>${e.title}</h3>
      <dl>
        <dt>Status</dt>
        <dd><zuaef-status-badge .status=${e.status??""}></zuaef-status-badge></dd>
        <dt>Kind</dt>
        <dd>${e.kind}</dd>
        ${e.step_index!==null?a`<dt>Step</dt><dd>#${e.step_index}</dd>`:d}
        <dt>Started</dt>
        <dd class=${e.started_at?"":"none"}>${e.started_at??"Unknown"}</dd>
        <dt>Finished</dt>
        <dd class=${e.finished_at?"":"none"}>${e.finished_at??"Unknown"}</dd>
        <dt>Duration</dt>
        <dd class=${e.duration_ms!==null?"":"none"}>
          ${e.duration_ms!==null?k(e.duration_ms):"Not derivable"}
        </dd>
        ${s?a`<dt>tool_call_id</dt><dd>${String(s)}</dd>`:d}
        ${e.detail?a`<dt>Error</dt><dd class="error-line">${e.detail}</dd>`:d}
        <dt>Derived from</dt>
        <dd>${e.source.join(", ")}</dd>
      </dl>
      ${this.renderEventPayloadHint(e)}
    `}renderEventPayloadHint(e){if(e.kind==="model_request"){const t=(e.payload.response_parts??[]).length>0;return a`<h4>Persisted data</h4>
        <p class="muted">
          ${t?"Per-response output parts are persisted (see Input/Output).":"No response message persisted for this request."}
        </p>`}if(e.kind==="tool_call"){const t=e.detail;return a`<h4>Persisted data</h4>
        <p class="muted">
          ${t?`Effect ledger: ${t}`:"No effect summary recorded."}
          Raw lifecycle events are under Raw.
        </p>`}return d}renderIo(e){const t=e.payload.response_parts??[];return t.length===0?a`<p class="muted">Not persisted</p>`:a`${t.map((s,r)=>this.renderPart(s,r))}`}renderPart(e,t){const s=typeof e.content=="string"?e.content:null;return a`
      <div class="part">
        <h4>Response part #${t} · ${e.part_kind}</h4>
        ${e.tool_name?a`<dl><dt>Tool</dt><dd>${e.tool_name}</dd></dl>`:d}
        ${s!==null?this.renderText(s,e.truncated===!0):d}
        ${e.args?a`<details>
              <summary>args</summary>
              <pre>${JSON.stringify(e.args,null,2)}</pre>
            </details>`:d}
      </div>
    `}renderText(e,t){if(e.length<=Tt)return a`<pre>${e}</pre>`;const s=t||e.length>=X?" (already truncated by the API)":"";return a`<pre>${e.slice(0,Tt)}…</pre>
    <details>
      <summary>Show full text (${e.length.toLocaleString()} chars)${s}</summary>
      <pre>${e}</pre>
    </details>`}renderUsage(e){const t=e.usage??{};return a`
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
        ${typeof t.requests=="number"?a`<dt>Requests</dt><dd>${t.requests}</dd>`:d}
      </dl>
    `}renderRaw(e){const t=JSON.stringify(e.payload,null,2)??"{}";return a`
      <h3>Raw</h3>
      <p class="muted">Exactly what GET /api/runs returned for this row.</p>
      ${t.length>X?a`<p class="muted">Preview truncated at ${X.toLocaleString()} chars.</p>
            <pre>${t.slice(0,X)}…</pre>`:a`<pre>${t}</pre>`}
    `}renderRunOverview(){const e=this.projection;if(!e)return a`<p class="muted">Select a run.</p>`;const t=e.run,s=e.composition;return a`
      <h3>${t.display_label}</h3>
      <dl>
        <dt>Status</dt>
        <dd><zuaef-status-badge .status=${t.status}></zuaef-status-badge></dd>
        <dt>Run ID</dt>
        <dd>${t.run_id}</dd>
        ${t.conversation_id?a`<dt>Conversation</dt><dd>${t.conversation_id}</dd>`:d}
        ${t.parent_run_id?a`<dt>Parent run</dt><dd>${t.parent_run_id}</dd>`:d}
        ${t.continued_from_run_id?a`<dt>Continued from</dt><dd>${t.continued_from_run_id}</dd>`:d}
        <dt>Model</dt>
        <dd class=${t.model?"":"none"}>${t.model??"Unknown"}</dd>
        <dt>Profile</dt>
        <dd class=${t.profile?"":"none"}>${t.profile??"Unknown"}</dd>
        ${t.agent_name?a`<dt>Agent</dt><dd>${t.agent_name}</dd>`:d}
        <dt>Started</dt>
        <dd class=${t.started_at?"":"none"}>${jt(t.started_at)||"Unknown"}</dd>
        <dt>Finished</dt>
        <dd class=${t.finished_at?"":"none"}>${jt(t.finished_at)||"Unknown"}</dd>
        <dt>Duration</dt>
        <dd class=${t.duration_ms!==null?"":"none"}>
          ${t.duration_ms!==null?k(t.duration_ms):"Not derivable"}
        </dd>
        <dt>Requests</dt>
        <dd>${t.request_count}</dd>
        <dt>Tool calls</dt>
        <dd>${t.tool_call_count}</dd>
      </dl>

      <h4>Usage</h4>
      ${e.usage?a`<dl>
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
          </dl>`:a`<p class="muted">Not persisted</p>`}

      <h4>Composition</h4>
      ${s?a`<details>
            <summary>${s.profile??"composition recorded"}</summary>
            <pre>${JSON.stringify(s,null,2)}</pre>
          </details>`:a`<p class="muted">Receipt unavailable</p>`}

      ${e.pause?a`<h4>Pause</h4>
            <p class="muted">
              Paused with ${e.pause.pending_approvals.length} pending
              approval(s). Supervision actions are not part of this read-only build.
            </p>`:d}

      ${e.unresolved_effects.length>0?a`<h4>Unresolved effects</h4>
            <pre>${JSON.stringify(e.unresolved_effects,null,2)}</pre>`:d}

      ${e.diagnostics.length>0?a`<h4>Diagnostics</h4>
            ${e.diagnostics.map(r=>a`<p class="diag">${r}</p>`)}`:d}

      ${e.artifacts.length>0?a`<h4>Artifacts</h4>
            ${e.artifacts.map(r=>a`<p class="muted">
                ${r.path}${r.size!==null?` — ${Lt(r.size)}`:""}
              </p>`)}`:d}
    `}};M.styles=z`
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
  `;at([h({attribute:!1})],M.prototype,"projection",2);at([h()],M.prototype,"selectedEventId",2);at([h()],M.prototype,"inspectorTab",2);M=at([w("zuaef-inspector")],M);const je={summary:"Summary",io:"Input/Output",usage:"Usage",raw:"Raw"};var Te=Object.defineProperty,Ie=Object.getOwnPropertyDescriptor,bt=(e,t,s,r)=>{for(var i=r>1?void 0:r?Ie(t,s):t,n=e.length-1,o;n>=0;n--)(o=e[n])&&(i=(r?o(t,s,i):o(i))||i);return r&&i&&Te(t,s,i),i};let W=class extends m{constructor(){super(...arguments),this.selected=!1}select(){this.dispatchEvent(new CustomEvent("run-selected",{detail:{runId:this.run.run_id},bubbles:!0,composed:!0}))}render(){const e=this.run,t=[e.model,e.profile].filter(Boolean).join(" · ");return a`
      <button
        role="option"
        aria-selected=${this.selected?"true":"false"}
        title=${`${e.display_label} — ${e.status} (${e.started_at??"unknown start"})`}
        @click=${this.select}
      >
        <span class="glyph ${e.status}" aria-hidden="true"
          >${Ue(e.status)}</span
        >
        <span class="label">${e.display_label}</span>
        <span class="time">${me(e.started_at)}</span>
        ${t?a`<span class="meta">${t}</span>`:a`<span class="meta">no model/profile recorded</span>`}
      </button>
    `}};W.styles=z`
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
  `;bt([h({attribute:!1})],W.prototype,"run",2);bt([h({type:Boolean})],W.prototype,"selected",2);W=bt([w("zuaef-run-row")],W);function Ue(e){switch(e){case"completed":return"✓";case"failed":return"✗";case"paused":return"⏸";case"limit_reached":return"⏹";case"incomplete":case"started":return"●";default:return"?"}}var Ne=Object.defineProperty,Me=Object.getOwnPropertyDescriptor,D=(e,t,s,r)=>{for(var i=r>1?void 0:r?Me(t,s):t,n=e.length-1,o;n>=0;n--)(o=e[n])&&(i=(r?o(t,s,i):o(i))||i);return r&&i&&Ne(t,s,i),i};let S=class extends m{constructor(){super(...arguments),this.runs=[],this.selectedRunId="",this.nextCursor=null,this.loadingMore=!1,this.filter=""}onFilter(e){this.dispatchEvent(new CustomEvent("run-filter",{detail:{value:e.target.value},bubbles:!0,composed:!0}))}passesFilter(e){return this.filter===""?!0:De(e,this.filter)}render(){const e=this.runs.filter(i=>this.passesFilter(i)),t=[["Today",[]],["Yesterday",[]],["Older",[]]];for(const i of e)t[["Today","Yesterday","Older"].indexOf(ge(i))][1].push(i);const s=e.length,r=this.runs.length;return a`
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
        ${r===0?a`<div class="state">Loading runs…</div>`:s===0?a`<div class="state">No runs match this filter.</div>`:t.map(([i,n])=>n.length>0?a`
                        <div class="group">${i}</div>
                        ${n.map(o=>a`
                            <zuaef-run-row
                              role="option"
                              .run=${o}
                              ?selected=${o.run_id===this.selectedRunId}
                            ></zuaef-run-row>
                          `)}
                      `:"")}
      </div>
      ${this.nextCursor?a`<button
            class="more"
            ?disabled=${this.loadingMore}
            @click=${()=>this.dispatchEvent(new CustomEvent("load-more",{bubbles:!0,composed:!0}))}
          >
            ${this.loadingMore?"Loading…":`Load more (${s} of ${r}+ loaded)`}
          </button>`:a`<div class="count">${s}${s<r?` of ${r}`:""} runs</div>`}
    `}};S.styles=z`
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
  `;D([h({attribute:!1})],S.prototype,"runs",2);D([h()],S.prototype,"selectedRunId",2);D([h({attribute:!1})],S.prototype,"nextCursor",2);D([h({type:Boolean})],S.prototype,"loadingMore",2);D([h()],S.prototype,"filter",2);S=D([w("zuaef-run-list")],S);function De(e,t){return[e.display_label,e.run_id,e.model,e.profile,e.status].filter(Boolean).join(`
`).toLowerCase().includes(t.toLowerCase())}var Le=Object.defineProperty,He=Object.getOwnPropertyDescriptor,_t=(e,t,s,r)=>{for(var i=r>1?void 0:r?He(t,s):t,n=e.length-1,o;n>=0;n--)(o=e[n])&&(i=(r?o(t,s,i):o(i))||i);return r&&i&&Le(t,s,i),i};const qe={run:"RUN",model_request:"REQ",tool_call:"TOOL"};let Z=class extends m{constructor(){super(...arguments),this.selected=!1}select(){this.dispatchEvent(new CustomEvent("event-selected",{detail:{rowId:this.row.id},bubbles:!0,composed:!0}))}render(){const e=this.row,t=e.kind==="run",s=qe[e.kind]??"EVENT",r=e.kind==="tool_call"?"tool":t?"run":"request";return a`
      <button
        role="option"
        aria-selected=${this.selected?"true":"false"}
        class=${[r,e.status?`state-${e.status}`:""].join(" ")}
        title=${e.title}
        @click=${this.select}
      >
        <span class="time">${I(e.started_at)}</span>
        <span class="kind">${t?"":s}</span>
        <span class="step">${e.step_index!==null?`#${e.step_index}`:""}</span>
        <span class="summary"
          >${e.title}${e.detail?a` <span class="detail">— ${e.detail}</span>`:""}</span
        >
        <span class="dur">${k(e.duration_ms)}</span>
        <span class="usage">${$e(e.usage)}</span>
        <span class="status ${e.status??""}"
          >${e.status?`${qt(e.status)} ${e.status}`:""}</span
        >
      </button>
    `}};Z.styles=z`
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
  `;_t([h({attribute:!1})],Z.prototype,"row",2);_t([h({type:Boolean})],Z.prototype,"selected",2);Z=_t([w("zuaef-event-row")],Z);var Be=Object.defineProperty,Fe=Object.getOwnPropertyDescriptor,J=(e,t,s,r)=>{for(var i=r>1?void 0:r?Fe(t,s):t,n=e.length-1,o;n>=0;n--)(o=e[n])&&(i=(r?o(t,s,i):o(i))||i);return r&&i&&Be(t,s,i),i};const Ge=[{id:"latency",label:"Latency"},{id:"input",label:"Input tokens"},{id:"output",label:"Output tokens"}];let j=class extends m{constructor(){super(...arguments),this.timeline=[],this.selectedEventId="",this.metric="latency",this.now=Date.now(),this.ticker=null}updated(e){super.updated(e);const t=this.timeline.some(s=>$t(s));t&&this.ticker===null?this.ticker=setInterval(()=>{this.now=Date.now()},1e3):!t&&this.ticker!==null&&(clearInterval(this.ticker),this.ticker=null)}disconnectedCallback(){super.disconnectedCallback(),this.ticker!==null&&clearInterval(this.ticker),this.ticker=null}select(e){this.dispatchEvent(new CustomEvent("event-selected",{detail:{rowId:e},bubbles:!0,composed:!0}))}tipLines(e){const t=e.row,s=[a`<div>${t.title}</div>`,a`<div class="muted">${I(t.started_at)}</div>`];return e.active?s.push(a`<div class="muted">
          elapsed ${k(this.now-(Date.parse(t.started_at??"")||0))}
        </div>`):t.duration_ms!==null&&s.push(a`<div class="muted">latency ${k(t.duration_ms)}</div>`),t.usage?.input_tokens!==void 0&&s.push(a`<div class="muted">in ${rt(t.usage.input_tokens)}</div>`),t.usage?.output_tokens!==void 0&&s.push(a`<div class="muted">out ${rt(t.usage.output_tokens)}</div>`),t.status&&t.status!=="completed"&&s.push(a`<div class="muted">${qt(t.status)} ${t.status}</div>`),s}render(){const e=Ae(this.timeline,this.metric,this.now);if(e.bars.length===0)return"";const t=e.bars.find(s=>s.active);return a`
      <div class="head">
        <span class="label">OVERVIEW</span>
        ${Ge.map(s=>a`<button
            class="metric"
            aria-pressed=${this.metric===s.id?"true":"false"}
            @click=${()=>{this.metric=s.id}}
          >
            ${s.label}
          </button>`)}
        <span class="spacer"></span>
        ${t?a`<span class="active-note">
              ${t.row.title} running ·
              ${k(this.now-(Date.parse(t.row.started_at??"")||0))}
              elapsed
            </span>`:""}
      </div>
      <div class="plot" role="group" aria-label="Request overview minimap">
        ${e.ticks.map(s=>a`<span
            class=${["tick",s.row.id===this.selectedEventId?"selected":"",s.row.status?`state-${s.row.status}`:""].join(" ")}
            style="left: ${(s.x*100).toFixed(3)}%"
            title=${s.row.title}
          ></span>`)}
        ${e.bars.map(s=>{const r=s.row.id===this.selectedEventId,i=["bar",s.active?"active":"",s.row.status&&!s.active?`state-${s.row.status}`:""].join(" ");return a`<button
            class=${i}
            role="option"
            aria-selected=${r?"true":"false"}
            aria-label=${`${s.row.title} at ${I(s.row.started_at)}`}
            style=${`left: ${(s.x*100).toFixed(3)}%; height: ${(s.h*100).toFixed(1)}%`}
            title=${s.row.title}
            @click=${()=>this.select(s.row.id)}
          >
            <span class="tip">${this.tipLines(s)}</span>
          </button>`})}
        ${t?a`<span
              class="nowline"
              style="left: 100%"
              title="now"
            ></span>`:""}
      </div>
      <div class="axis">
        <span>${I(new Date(e.t0).toISOString())}</span>
        <span>${t?"NOW":I(new Date(e.t1).toISOString())}</span>
      </div>
    `}};j.styles=z`
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
  `;J([h({attribute:!1})],j.prototype,"timeline",2);J([h()],j.prototype,"selectedEventId",2);J([b()],j.prototype,"metric",2);J([b()],j.prototype,"now",2);j=J([w("zuaef-overview-strip")],j);var Ve=Object.defineProperty,We=Object.getOwnPropertyDescriptor,L=(e,t,s,r)=>{for(var i=r>1?void 0:r?We(t,s):t,n=e.length-1,o;n>=0;n--)(o=e[n])&&(i=(r?o(t,s,i):o(i))||i);return r&&i&&Ve(t,s,i),i};let P=class extends m{constructor(){super(...arguments),this.projection=null,this.loading=!1,this.selectedEventId="",this.error="",this.expandedGroups=[],this.lastRunId=null}updated(e){super.updated(e),(e.has("selectedEventId")||e.has("projection"))&&this.scrollToSelected()}scrollToSelected(){const e=this.selectedEventId;if(e){for(const t of this.renderRoot.querySelectorAll("zuaef-event-row"))if(t.row?.id===e){t.scrollIntoView({block:"nearest",behavior:"smooth"});return}}}toggleGroup(e){this.expandedGroups=this.expandedGroups.includes(e)?this.expandedGroups.filter(t=>t!==e):[...this.expandedGroups,e]}isOpen(e){return this.expandedGroups.includes(e.groupId)||ye(e,this.selectedEventId)}groupTotal(e){const t=e.rows.reduce((s,r)=>r.duration_ms!==null?s+r.duration_ms:s,0);return t>0?k(t):""}renderEntry(e){if(!_e(e))return a`<zuaef-event-row
        role="option"
        .row=${e}
        ?selected=${e.id===this.selectedEventId}
        @event-selected=${i=>this.dispatchEvent(new CustomEvent("event-selected",{detail:i.detail,bubbles:!0,composed:!0}))}
      ></zuaef-event-row>`;const t=this.isOpen(e),s=e.rows[0],r=a`<button
      class="group-header"
      aria-expanded=${t?"true":"false"}
      title=${`${e.toolName} ×${e.rows.length} — click to ${t?"collapse":"expand"}`}
      @click=${()=>this.toggleGroup(e.groupId)}
    >
      <span class="time">${I(s.started_at)}</span>
      <span class="kind">TOOL</span>
      <span class="step"></span>
      <span class="summary"
        ><span class="caret" aria-hidden="true">${t?"▾":"▸"}</span
        >${e.toolName} ×${e.rows.length}</span
      >
      <span class="dur">${this.groupTotal(e)}</span>
      <span class="usage"></span>
      <span class="status">${e.rows.length} calls</span>
    </button>`;return t?a`${r}
      ${e.rows.map(i=>this.renderEntry(i))}`:r}render(){const e=this.projection?.run;return e&&e.run_id!==this.lastRunId&&(this.lastRunId=e.run_id,this.expandedGroups=[]),a`
      <header>
        <h2>${e?e.display_label:"Trajectory"}</h2>
        ${e?a`<zuaef-status-badge .status=${e.status}></zuaef-status-badge>`:""}
        ${e&&e.model?a`<span class="model">${e.model}</span>`:""}
      </header>
      ${this.projection?.diagnostics?.length?this.projection.diagnostics.map(t=>a`<div class="diag">${t}</div>`):""}
      ${this.projection&&!this.error?a`<zuaef-overview-strip
            .timeline=${this.projection.timeline}
            .selectedEventId=${this.selectedEventId}
            @event-selected=${t=>this.dispatchEvent(new CustomEvent("event-selected",{detail:t.detail,bubbles:!0,composed:!0}))}
          ></zuaef-overview-strip>`:""}
      <div class="scroll">
        ${this.error?a`<div class="state error">${this.error}</div>`:this.loading?a`<div class="state">Loading trajectory…</div>`:this.projection?this.projection.timeline.length===0?a`<div class="state">
                    No step events persisted for this run — only receipt-level facts exist.
                  </div>`:xe(this.projection.timeline).map(t=>this.renderEntry(t)):a`<div class="state">Select a run to inspect its trajectory.</div>`}
      </div>
    `}};P.styles=z`
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
  `;L([h({attribute:!1})],P.prototype,"projection",2);L([h({type:Boolean})],P.prototype,"loading",2);L([h()],P.prototype,"selectedEventId",2);L([h()],P.prototype,"error",2);L([b()],P.prototype,"expandedGroups",2);P=L([w("zuaef-trajectory-view")],P);var Ze=Object.defineProperty,Ke=Object.getOwnPropertyDescriptor,y=(e,t,s,r)=>{for(var i=r>1?void 0:r?Ke(t,s):t,n=e.length-1,o;n>=0;n--)(o=e[n])&&(i=(r?o(t,s,i):o(i))||i);return r&&i&&Ze(t,s,i),i};let $=class extends m{constructor(){super(...arguments),this.ui=ve,this.runs=[],this.nextCursor=null,this.loadingMore=!1,this.projection=null,this.projectionLoading=!1,this.projectionError="",this.live=!0,this.liveAvailable=!0,this.es=null,this.esRunId=void 0,this.invalidateTimer=null}connectedCallback(){super.connectedCallback(),this.reloadRuns()}disconnectedCallback(){super.disconnectedCallback(),this.closeStream(),this.invalidateTimer!==null&&clearTimeout(this.invalidateTimer)}willUpdate(e){if(super.willUpdate(e),e.has("ui")||e.has("live")||e.has("liveAvailable")){const t=e.get("ui");(!t||t.selectedRunId!==this.ui.selectedRunId)&&this.ui.selectedRunId&&(this.live=!0),this.syncStream()}}closeStream(){this.es?.close(),this.es=null,this.esRunId=void 0}syncStream(){const e=this.live&&this.liveAvailable?this.ui.selectedRunId:void 0;this.es&&this.esRunId===e||(this.closeStream(),e&&(this.es=new EventSource(Y.runEventsUrl(e)),this.esRunId=e,this.es.addEventListener("run_changed",()=>this.scheduleInvalidate()),this.es.onerror=()=>{this.liveAvailable=!1,this.closeStream()}))}scheduleInvalidate(){this.invalidateTimer!==null&&clearTimeout(this.invalidateTimer),this.invalidateTimer=setTimeout(()=>{this.invalidateTimer=null,!(!this.live||!this.ui.selectedRunId)&&(this.reloadProjection(this.ui.selectedRunId),this.reloadRuns())},150)}setLive(e){e&&!this.liveAvailable||(this.live=e,e&&this.ui.selectedRunId&&(this.reloadProjection(this.ui.selectedRunId),this.reloadRuns()))}async reloadRuns(){try{const e=await Y.listRuns();this.runs=e.runs,this.nextCursor=e.next_cursor,!this.ui.selectedRunId&&this.runs.length>0?this.selectRun(this.runs[0].run_id):this.ui.selectedRunId&&this.reloadProjection(this.ui.selectedRunId)}catch(e){this.projectionError=`Failed to load runs: ${ct(e)}`}}async loadMore(e){this.loadingMore=!0;try{const t=await Y.listRuns(e),s=new Set(this.runs.map(r=>r.run_id));this.runs=[...this.runs,...t.runs.filter(r=>!s.has(r.run_id))],this.nextCursor=t.next_cursor}catch(t){this.projectionError=`Failed to load more runs: ${ct(t)}`}finally{this.loadingMore=!1}}async reloadProjection(e){this.projectionLoading=!this.projection||this.projection.run.run_id!==e,this.projectionLoading&&(this.projectionError="");try{this.projection=await Y.getRun(e),this.projectionError="",document.title=`${this.projection.run.display_label} — ZUAEF Console`}catch(t){this.projectionError=`Failed to load run: ${ct(t)}`}finally{this.projectionLoading=!1}}patchUi(e){this.ui={...this.ui,...e}}selectRun(e){e!==this.ui.selectedRunId&&(this.patchUi({selectedRunId:e,selectedEventId:void 0}),this.reloadProjection(e))}render(){const e=this.projection?.run??null,t=e?[e.model??"model unknown",e.profile??"profile unknown"].join(" · "):"";return a`
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
          .selectedEventId=${this.ui.selectedEventId??""}
          .inspectorTab=${this.ui.inspectorTab}
          @tab-selected=${s=>this.patchUi({inspectorTab:s.detail.tab})}
        ></zuaef-inspector>
      </div>
      <zuaef-artifact-bar
        .artifacts=${this.projection?.artifacts??[]}
        .pause=${this.projection?.pause??null}
      ></zuaef-artifact-bar>
    `}async refresh(){await this.reloadRuns()}};$.styles=z`
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
  `;y([h({attribute:!1})],$.prototype,"ui",2);y([b()],$.prototype,"runs",2);y([b()],$.prototype,"nextCursor",2);y([b()],$.prototype,"loadingMore",2);y([b()],$.prototype,"projection",2);y([b()],$.prototype,"projectionLoading",2);y([b()],$.prototype,"projectionError",2);y([b()],$.prototype,"live",2);y([b()],$.prototype,"liveAvailable",2);$=y([w("zuaef-console")],$);function ct(e){return e instanceof Error?e.message:String(e)}
