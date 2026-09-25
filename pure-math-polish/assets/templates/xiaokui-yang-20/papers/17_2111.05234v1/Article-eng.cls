%%%% Basée sur la classe "article, 11pt, A4"

%\LoadClass[11pt,A4]{article}
\LoadClass[12pt,A4]{amsart}

%%%% Choix des packages Latex 
%\PassOptionsToPackage{dvipsnames,svgnames}{xcolor}

\RequirePackage{calligra,amsmath,amsthm,mathrsfs,mathtools,graphicx,xcolor,comment,bbm,framed}
%\RequirePackage[pdfpagemode=UseNone,bookmarksopen=false,colorlinks=true,urlcolor=blue,citecolor=blue,citebordercolor=blue,linkcolor=blue]{hyperref}
\RequirePackage[utf8]{inputenc}
\RequirePackage[T1]{fontenc}
\RequirePackage[english]{babel}
%\RequirePackage{dsfont}

%\RequirePackage[slantedGreeks]{kpfonts}
\RequirePackage{stix2}
%\let\mathfrak\undefined
%\RequirePackage{eufrak}
\RequirePackage{ifthen,setspace,enumitem,tikz}
\usetikzlibrary{arrows}
%\RequirePackage{fancyhdr}


%\usepackage{mathtools}
%\usepackage{extpfeil} % package for extensible arrows, Attention, this package changes \mathbb in kpfonts to the usual one !
%\reversemarginpar
%\RequirePackage[font=sf, labelfont={sf,bf}, margin=1cm]{caption}
%\setlength{\marginparwidth}{2cm}
%\usepackage[toc,page]{appendix}

%\usepackage{tocloft}
%\addto\captionsenglish{% Replace "english" with the language you use
%  \renewcommand{\contentsname}%
%    {\hspace{12.5em}\LARGE Contents\hfill}%
%}
%\usepackage[new]{old-arrows}


%%%% Mise en page
\setlength{\marginparwidth}{2cm}
%\linespread{1.2}
\usepackage[a4paper,top=3cm,bottom=2cm,left=3cm,right=3cm,marginparwidth=2cm]{geometry}
%\RequirePackage[colorinlistoftodos,color=blue!50!white, textsize=tiny,textwidth=1.5cm,shadow]{todonotes}


\usepackage[toc,page]{appendix}

%%%% Définition des caractères mathématiques
\newcommand{\rightarrowdbl}{\rightarrow\mathrel{\mkern-14mu}\rightarrow}

\newcommand{\xrightarrowdbl}[2][]{%
  \xrightarrow[#1]{#2}\mathrel{\mkern-14mu}\rightarrow
}
% twohead version of \xrightarrow

\newcommand{\inv}{^{-1}}
\newcommand{\univ}{^{\text{\tiny univ}}}
\newcommand{\Z[1]}{\mathbb{Z}/#1\mathbb{Z}} % groupe/anneau des entiers modulo n 
%\newcommand{\lcm[2]}{\text{lcm}(#1,#2)}
\newcommand{\GSym[1]}{\mathop{\mathfrak{S}}\nolimits_{#1}}  % groupes symétriques
\newcommand{\ptensor[1]}{^{\otimes {#1}}}
\newcommand{\SheafHom[1]}{\mathscr{H}\!\!\!\text{\calligra om}_{\,{#1}}}
\newcommand{\SheafExt[2]}{\mathscr{E}\!\!\text{\calligra xt}_{\,{#1}}^{\;\;{#2}}}
\newcommand{\HyperExt[2]}{\mathbbm{Ext}_{{#1}}^{{#2}}}

\def \RDer {\text{\sf R}} % foncteur dérivé à droite
\def \LDer {\text{\sf L}} % foncteur dérivé à gauche
\def \HyperCoh {\mathbbm H} % hypercohomologie
\def \NN {\mathbb N} % nombres naturels
\def \ZZ {\mathbb Z} % entiers
\def \CC {\mathbb C} % nombres complexes
\def \RR {\mathbb R} % nombres réels
\def \QQ {\mathbb Q} % nombres rationels
\def \AFF {\mathbb A} %espaces affines
\def \PP {\mathbb P}  % espaces projectifs
\def \FF {\mathbb F} % corps fini

%\def \BB {\mathbb B}
%\def \UU {\mathbb U}
\def \GG {\mathbb G} % groupe asditif/multiplicatif
\def \scrA {\mathscr A}
\def \scrB {\mathscr B}
\def \scrO {\mathscr O} % faisceau structurel des anneaux
\def \scrD {\mathscr D} 
\def \scrE {\mathscr E} % faisceau
\def \scrF {\mathscr F} % faisceau
\def \scrG {\mathscr G} % faisceau
\def \scrH {\mathscr H} % faisceau
\def \scrI {\mathscr I} % faisceau (idéal)
\def \scrJ {\mathscr J} % faisceau (idéal)
\def \scrK {\mathscr K} % faisceau (noyau d'un morphisme)
\def \scrL {\mathscr L} % faisceau inversible
\def \scrM {\mathscr M} % faisceau
\def \scrN {\mathscr N} % faisceau/fibré normal
\def \scrP {\mathscr P} % fibré en droites de Poincaré
\def \scrU {\mathscr U} % faisceau
\def \scrV {\mathscr V} % faisceau
\def \scrW {\mathscr W} % faisceau

\def \fraka {\mathfrak a} % idéal
\def \frakb {\mathfrak b} % idéal / idéal de base

\DeclareMathOperator{\Spec}{Spec} % le spectre d'un anneau
\DeclareMathOperator{\pr}{pr} % projection naturelle
\DeclareMathOperator{\codim}{codim} % la codimension
\DeclareMathOperator{\Aut}{Aut} % groupes des automorphismes
\DeclareMathOperator{\Inn}{Inn} % groupes des automorphismes intérieures
\DeclareMathOperator{\End}{End} % espaces des endomorphismes
\DeclareMathOperator{\Hom}{Hom} % espaces des morphismes
\DeclareMathOperator{\Ext}{Ext} % foncteur ext
\DeclareMathOperator{\Ker}{Ker} % noyau d'un morphisme
\DeclareMathOperator{\Image}{Im} % image d'un morphisme
\DeclareMathOperator{\Coker}{Coker} % conoyau d'un morphisme
%\DeclareMathOperator{\Coim}{Coim} % coimage d'un morphisme
\DeclareMathOperator{\Supp}{Supp} % support d'un faisceau/module
\DeclareMathOperator{\trace}{tr} % trace d'une matrice/endomorphisme linéaire
\DeclareMathOperator{\GL}{GL} % groupes linéaires généraux
\DeclareMathOperator{\PGL}{PGL}
\DeclareMathOperator{\SL}{SL} % groupes linéaires spéciaux
\DeclareMathOperator{\Orth}{O} % groupes orthogonaux
\DeclareMathOperator{\SO}{SO} % groupes orthogonaux spéciaux
\DeclareMathOperator{\Unitary}{U} % groupes unitaires
\DeclareMathOperator{\SU}{SU} % groupes unitaires spéciaux
\DeclareMathOperator{\Mat}{Mat} % espace des matrices
\DeclareMathOperator{\Isom}{Isom} % groupes des isométries
\DeclareMathOperator{\AffT}{Aff} % groupes des transformations affines
\DeclareMathOperator{\id}{id} % morphisme l'identité
\DeclareMathOperator{\Coh}{H} % groupes homologie ou cohomologie
\DeclareMathOperator{\dimcoh}{h} % dimension des groupes cohomologie
\DeclareMathOperator{\alb}{alb} % application d'Albanese
\DeclareMathOperator{\Alb}{Alb} % tore d'Albanese
\DeclareMathOperator{\Pic}{Pic} % groupe de Picard
\DeclareMathOperator{\rank}{rk} % rang d'un module libre / groupe abélien libre 
\DeclareMathOperator{\red}{red} % schéma réduit associé à un schéma
\DeclareMathOperator{\reg}{reg} % lieu lisse d'un espace analytique complexe
\DeclareMathOperator{\sing}{sing} % lieu singulier d'un espace analytique complexe
\DeclareMathOperator{\Sing}{Sing} % lieu singulier d'un champs de Pfaff / feuilletage
%\DeclareMathOperator{\norm}{norm} % lieu normal d'un espace analytique complexe
\DeclareMathOperator{\tor}{tor} % torsion
\DeclareMathOperator{\num}{num} % équivalence numérique pour les cycles algébriques/analytiques
\DeclareMathOperator{\chern}{c} % classe de Chern
\DeclareMathOperator{\Eff}{Eff} % cône des diviseurs effectifs
\DeclareMathOperator{\Gros}{Big} % cône des diviseurs gros
\DeclareMathOperator{\Nef}{Nef} % cône des diviseurs nefs
\DeclareMathOperator{\Amp}{Amp} % cône des diviseurs amples
\DeclareMathOperator{\NS}{NS} % espace/groupe de Nérons-Severi
\DeclareMathOperator{\NE}{NE} % cône des courbes effectives
\DeclareMathOperator{\Psef}{Psef} % espace des diviseurs/classe transcendantes pseudo-effectifs 
\DeclareMathOperator{\Sym}{Sym} % produit symétrique 
\DeclareMathOperator{\Bs}{Bs} % lieu de base (schématique)
\DeclareMathOperator{\divisor}{div} % diviseur de zéro d'une section d'un fibré en droites / diviseur d'une fonction méromorphe 
\DeclareMathOperator{\exceptional}{exc}
\DeclareMathOperator{\Exceptional}{Exc}
\DeclareMathOperator{\horizontal}{horiz}
\DeclareMathOperator{\vertical}{vert}
\DeclareMathOperator{\orbifold}{orb}
\DeclareMathOperator{\order}{ord}
\DeclareMathOperator{\multiplicity}{mult}
\DeclareMathOperator{\Ramification}{Ram} % lieu de ramification 
\DeclareMathOperator{\Branch}{Branch} % lieu de branchement 
\DeclareMathOperator{\Cond}{Cond} % divisieur conducteur
\DeclareMathOperator{\Blowup}{Bl}
\newcommand{\terminal}{\text{\rm\tiny term}}
\newcommand{\qf}{\text{\rm\tiny qf}}

\newcommand{\BottChern}{\Coh_{\,\text{\rm\tiny BC}}} % cohmoologie de Bott-Chern
\newcommand{\BC}{\BottChern^{1,1}} % Cohomologie de Bott-Chern des (1,1)-forme avec potentiel local


%%%%% Définition des environnements pour théorèmes, lemmes, corollaires, remarques, etc.
\theoremstyle{plain}
\newtheorem{mainthm}{Theorem}
\renewcommand\themainthm{\Alph{mainthm}}
\newtheorem{maincor}[mainthm]{Corollary}

\newtheorem{prop}{Proposition}[section]
\newtheorem{conj}[prop]{Conjecture}
\newtheorem{thm}[prop]{Theorem}
\newtheorem{lemme}[prop]{Lemma}
\newtheorem{cor}[prop]{Corollary}
\newtheorem{ques}[prop]{Question}


\theoremstyle{definition}
\newtheorem{defn}[prop]{Definition}%
\newtheorem{prop-defn}[prop]{Proposition-Definition}%
\newtheorem{claim}{Claim}%
\newtheorem{setting}[prop]{General Setting}
\newtheorem{assumption}[prop]{Assumption}
\newtheorem{notation}[prop]{Notation}
\newtheorem{exa}[prop]{Example}
%\renewcommand\theaffirm{(\roman{affirm})}
\theoremstyle{remark} 
\newtheorem{rmq}[prop]{Remark}

%newtheorem*{convention}{Convention}