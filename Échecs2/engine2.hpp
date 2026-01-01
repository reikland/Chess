#pragma once
#include <cstdint>
#include <algorithm>
#include <chrono>
#include <limits>
#include <string>

namespace cechess {

using U64 = std::uint64_t;
constexpr int INF  = 30000;
constexpr int MATE = 29000;
constexpr int FUTILITY_MARGIN = 150;

enum Color { WHITE=0, BLACK=1 };
enum PieceType { PAWN=0, KNIGHT, BISHOP, ROOK, QUEEN, KING, NO_PIECE_TYPE };
enum Piece {
    EMPTY=0,
    W_PAWN, W_KNIGHT, W_BISHOP, W_ROOK, W_QUEEN, W_KING,
    B_PAWN, B_KNIGHT, B_BISHOP, B_ROOK, B_QUEEN, B_KING
};
enum MoveFlag {
    MF_QUIET=0,
    MF_CAPTURE   = 1<<24,
    MF_ENPASSANT = 1<<25,
    MF_KSCASTLE  = 1<<26,
    MF_QSCASTLE  = 1<<27,
    MF_PROMO     = 1<<28
};

// --- Utilitaires de base ---

inline int piece_color(Piece p){ return p>=B_PAWN; }
inline int piece_type(Piece p){ return p ? ((p-1)%6) : NO_PIECE_TYPE; }
inline Piece make_piece(Color c, PieceType t){ return t==NO_PIECE_TYPE ? EMPTY : Piece(1+t+6*c); }

inline int sq(int f,int r){ return r*8+f; }
inline int file_of(int s){ return s & 7; }
inline int rank_of(int s){ return s >> 3; }

inline int move_from(int m){ return m & 63; }
inline int move_to(int m){ return (m >> 6) & 63; }
inline int move_promo(int m){ return (m >> 12) & 7; }
inline bool move_is_capture(int m){ return m & MF_CAPTURE; }
inline bool move_is_promo(int m){ return m & MF_PROMO; }

inline int make_move_int(int from,int to,int promo=0,int flags=0){
    return from | (to<<6) | (promo<<12) | flags;
}

inline U64 bb_one(int s){ return 1ULL << s; }
inline int pop_lsb(U64 &b){ int s=__builtin_ctzll(b); b &= b-1; return s; }
inline int bb_count(U64 b){ return __builtin_popcountll(b); }

// --- Structures ---

struct Position {
    Piece board[64]{};
    U64 bb[2][6]{};      // [color][pieceType]
    U64 occ[2]{}, occ_all{};
    Color stm = WHITE;
    int castling = 0;    // bits: 1=WK,2=WQ,4=BK,8=BQ
    int ep = -1;
    int halfmove = 0, fullmove = 1;
    U64 key = 0;
};

struct Undo {
    Position prev;       // snapshot complet
};

// --- Transposition table ---

struct TTEntry {
    U64 key = 0;
    int16_t score = 0;
    uint16_t move = 0;
    int8_t depth = 0;
    uint8_t flag = 0;
};

constexpr int TT_BITS = 20; // 1M entrées
constexpr int TT_SIZE = 1<<TT_BITS;
static TTEntry TT[TT_SIZE];

// --- Heuristiques de recherche ---

constexpr int MAX_PLY = 64;
static int killer_moves[2][MAX_PLY]{};      // [2 killers][ply]
static int history_heur[2][64][64]{};       // [color][from][to]

// --- Historique de partie + recherche ---

static U64 game_history[4096]{}; // historique réel de la partie
static int game_ply = 0;

static U64 rep_history[4096]{};  // historique pour la recherche

// --- Zobrist & attaques ---

static U64 zob_piece[2][6][64], zob_castle[16], zob_ep[9], zob_side;
static U64 knight_att[64], king_att[64];

// MVV-LVA
static int MVV_LVA[7][7]; // [victimType][attackerType], 0..5 = pièces, 6 = empty

// Valeurs de base
static const int VAL[6] = {100,320,330,500,900,0};

// --- Initialisations ---

inline void init_zobrist(){
    std::uint64_t x=88172645463393265ULL;
    auto rnd=[&](){ x^=x<<7; x^=x>>9; return x; };
    for(int c=0;c<2;c++)
        for(int t=0;t<6;t++)
            for(int s=0;s<64;s++)
                zob_piece[c][t][s]=rnd();
    for(int i=0;i<16;i++) zob_castle[i]=rnd();
    for(int i=0;i<9;i++)  zob_ep[i]=rnd();
    zob_side=rnd();
}

inline void init_leapers(){
    for(int s=0;s<64;s++){
        int f=file_of(s), r=rank_of(s);
        U64 n=0,k=0;
        int nf[8]={1,2,2,1,-1,-2,-2,-1};
        int nr[8]={2,1,-1,-2,-2,-1,1,2};
        for(int i=0;i<8;i++){
            int ff=f+nf[i], rr=r+nr[i];
            if(ff>=0&&ff<8&&rr>=0&&rr<8)
                n |= bb_one(sq(ff,rr));
        }
        for(int ff=f-1;ff<=f+1;ff++)
            for(int rr=r-1;rr<=r+1;rr++)
                if(ff>=0&&ff<8&&rr>=0&&rr<8&&(ff!=f||rr!=r))
                    k |= bb_one(sq(ff,rr));
        knight_att[s]=n;
        king_att[s]=k;
    }
}

inline void init_mvv_lva(){
    for(int victim=0; victim<7; ++victim){
        for(int attacker=0; attacker<7; ++attacker){
            int v = (victim  <6 ? VAL[victim]  : 0);
            int a = (attacker<6 ? VAL[attacker]: 1);
            MVV_LVA[victim][attacker] = v*10 - a;
        }
    }
}

inline void init_all(){
    init_zobrist();
    init_leapers();
    init_mvv_lva();
}

// --- Attaques sliding ---

inline U64 rook_attacks(int sq0,U64 occ){
    U64 a=0;
    int f=file_of(sq0), r=rank_of(sq0);
    for(int rr=r+1;rr<8;rr++){int s=sq(f,rr); a|=bb_one(s); if(occ&bb_one(s))break;}
    for(int rr=r-1;rr>=0;rr--){int s=sq(f,rr); a|=bb_one(s); if(occ&bb_one(s))break;}
    for(int ff=f+1;ff<8;ff++){int s=sq(ff,r); a|=bb_one(s); if(occ&bb_one(s))break;}
    for(int ff=f-1;ff>=0;ff--){int s=sq(ff,r); a|=bb_one(s); if(occ&bb_one(s))break;}
    return a;
}

inline U64 bishop_attacks(int sq0,U64 occ){
    U64 a=0;
    int f=file_of(sq0), r=rank_of(sq0);
    for(int ff=f+1,rr=r+1;ff<8&&rr<8;ff++,rr++){int s=sq(ff,rr); a|=bb_one(s); if(occ&bb_one(s))break;}
    for(int ff=f-1,rr=r+1;ff>=0&&rr<8;ff--,rr++){int s=sq(ff,rr); a|=bb_one(s); if(occ&bb_one(s))break;}
    for(int ff=f+1,rr=r-1;ff<8&&rr>=0;ff++,rr--){int s=sq(ff,rr); a|=bb_one(s); if(occ&bb_one(s))break;}
    for(int ff=f-1,rr=r-1;ff>=0&&rr>=0;ff--,rr--){int s=sq(ff,rr); a|=bb_one(s); if(occ&bb_one(s))break;}
    return a;
}

inline U64 queen_attacks(int sq0,U64 occ){
    return rook_attacks(sq0,occ) | bishop_attacks(sq0,occ);
}

// --- Occupancy & zobrist ---

inline U64 compute_key(const Position &p){
    U64 k=0;
    for(int s=0;s<64;s++){
        Piece pc=p.board[s]; if(pc==EMPTY)continue;
        int c=piece_color(pc), t=piece_type(pc);
        k ^= zob_piece[c][t][s];
    }
    k ^= zob_castle[p.castling & 15];
    if(p.ep!=-1) k ^= zob_ep[file_of(p.ep)];
    if(p.stm==BLACK) k ^= zob_side;
    return k;
}

inline void update_occupancy(Position &p){
    p.occ[0]=p.occ[1]=p.occ_all=0;
    for(int c=0;c<2;c++)
        for(int t=0;t<6;t++)
            p.bb[c][t]=0;
    for(int s=0;s<64;s++){
        Piece pc=p.board[s]; if(pc==EMPTY)continue;
        int c=piece_color(pc), t=piece_type(pc);
        U64 b=bb_one(s);
        p.bb[c][t] |= b;
        p.occ[c]   |= b;
    }
    p.occ_all = p.occ[0] | p.occ[1];
}

// incrémental
inline void add_piece(Position &p, int s, Piece pc){
    p.board[s] = pc;
    if(pc==EMPTY) return;
    int c = piece_color(pc);
    int t = piece_type(pc);
    U64 b = bb_one(s);
    p.bb[c][t] |= b;
    p.occ[c]   |= b;
    p.occ_all  |= b;
    p.key ^= zob_piece[c][t][s];
}

inline void remove_piece(Position &p, int s){
    Piece pc = p.board[s];
    if(pc==EMPTY) return;
    int c = piece_color(pc);
    int t = piece_type(pc);
    U64 b = bb_one(s);
    p.bb[c][t] &= ~b;
    p.occ[c]   &= ~b;
    p.occ_all  &= ~b;
    p.key ^= zob_piece[c][t][s];
    p.board[s] = EMPTY;
}

inline void move_piece(Position &p, int from, int to){
    Piece pc = p.board[from];
    if(pc==EMPTY) return;
    int c = piece_color(pc);
    int t = piece_type(pc);
    U64 fb = bb_one(from), tb = bb_one(to);
    p.bb[c][t] ^= fb;
    p.bb[c][t] |= tb;
    p.occ[c]   ^= fb;
    p.occ[c]   |= tb;
    p.occ_all  ^= fb;
    p.occ_all  |= tb;
    p.key ^= zob_piece[c][t][from];
    p.key ^= zob_piece[c][t][to];
    p.board[from] = EMPTY;
    p.board[to]   = pc;
}

// position de départ
inline void set_startpos(Position &p){
    static const Piece start[64]={
        W_ROOK,W_KNIGHT,W_BISHOP,W_QUEEN,W_KING,W_BISHOP,W_KNIGHT,W_ROOK,
        W_PAWN,W_PAWN,W_PAWN,W_PAWN,W_PAWN,W_PAWN,W_PAWN,W_PAWN,
        EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,
        EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,
        EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,
        EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,EMPTY,
        B_PAWN,B_PAWN,B_PAWN,B_PAWN,B_PAWN,B_PAWN,B_PAWN,B_PAWN,
        B_ROOK,B_KNIGHT,B_BISHOP,B_QUEEN,B_KING,B_BISHOP,B_KNIGHT,B_ROOK
    };
    p = Position();
    for(int i=0;i<64;i++) p.board[i]=start[i];
    update_occupancy(p);
    p.stm      = WHITE;
    p.castling = 0b1111;
    p.ep       = -1;
    p.halfmove = 0;
    p.fullmove = 1;
    p.key      = compute_key(p);
}

// --- Attaques & check ---

inline bool square_attacked(const Position &p,int sq0,Color by){
    U64 occ=p.occ_all;
    int dir = by==WHITE?1:-1;
    int r=rank_of(sq0), f=file_of(sq0);
    int pr=r-dir;
    if(pr>=0&&pr<8){
        if(f>0 && p.board[sq(f-1,pr)]==make_piece(by,PAWN))return true;
        if(f<7 && p.board[sq(f+1,pr)]==make_piece(by,PAWN))return true;
    }
    if(knight_att[sq0] & p.bb[by][KNIGHT]) return true;
    if(king_att[sq0]   & p.bb[by][KING])   return true;
    if(bishop_attacks(sq0,occ) & (p.bb[by][BISHOP]|p.bb[by][QUEEN])) return true;
    if(rook_attacks(sq0,occ)   & (p.bb[by][ROOK]  |p.bb[by][QUEEN])) return true;
    return false;
}

inline bool in_check(const Position &p,Color side){
    U64 kbb=p.bb[side][KING]; if(!kbb) return false;
    int ks=__builtin_ctzll(kbb);
    return square_attacked(p,ks,(Color)(side^1));
}

// --- Génération de coups ---

inline int generate_moves(const Position &p,int *moves,bool captures_only=false){
    int n=0;
    Color us=p.stm, them=(Color)(us^1);
    U64 own=p.occ[us], opp=p.occ[them], occ=p.occ_all;
    int pawn_dir   = us==WHITE?1:-1;
    int start_rank = us==WHITE?1:6;
    int promo_rank = us==WHITE?6:1;
    int ep_rank    = us==WHITE?4:3;

    // Pions
    U64 pawns=p.bb[us][PAWN];
    while(pawns){
        int s=pop_lsb(pawns);
        int r=rank_of(s), f=file_of(s);
        int fr= r + pawn_dir;
        if(fr>=0&&fr<8){
            int forward=sq(f,fr);
            // Coups calmes / promotions calmes uniquement si !captures_only
            if(!captures_only){
                if(!(occ&bb_one(forward))){
                    if(r==promo_rank){
                        moves[n++]=make_move_int(s,forward,QUEEN, MF_PROMO);
                        moves[n++]=make_move_int(s,forward,ROOK,  MF_PROMO);
                        moves[n++]=make_move_int(s,forward,BISHOP,MF_PROMO);
                        moves[n++]=make_move_int(s,forward,KNIGHT,MF_PROMO);
                    }else{
                        moves[n++]=make_move_int(s,forward);
                        if(r==start_rank){
                            int ff=sq(f,fr+pawn_dir);
                            if(!(occ&bb_one(ff)))
                                moves[n++]=make_move_int(s,ff);
                        }
                    }
                }
            }
            // Captures & EP (toujours générées, y compris en quiescence)
            for(int df=-1; df<=1; df+=2){
                int ff=f+df; if(ff<0||ff>7) continue;
                int to=sq(ff,fr);

                if(opp&bb_one(to)){
                    // --- FIX: capture + promotion = 4 choix (Q/R/B/N)
                    if(r==promo_rank){
                        moves[n++]=make_move_int(s,to,QUEEN,  MF_CAPTURE|MF_PROMO);
                        moves[n++]=make_move_int(s,to,ROOK,   MF_CAPTURE|MF_PROMO);
                        moves[n++]=make_move_int(s,to,BISHOP, MF_CAPTURE|MF_PROMO);
                        moves[n++]=make_move_int(s,to,KNIGHT, MF_CAPTURE|MF_PROMO);
                    }else{
                        moves[n++]=make_move_int(s,to,0,MF_CAPTURE);
                    }
                }else if(p.ep==to && r==ep_rank){
                    moves[n++]=make_move_int(s,to,0,MF_CAPTURE|MF_ENPASSANT);
                }
            }
        }
    }

    // Mode quiescence : on ne génère ensuite que des captures pour les pièces lourdes / roi
    if(captures_only){
        // Cavaliers
        U64 bbp=p.bb[us][KNIGHT];
        while(bbp){
            int s=pop_lsb(bbp);
            U64 t = knight_att[s] & opp;
            while(t){
                int to=pop_lsb(t);
                moves[n++]=make_move_int(s,to,0,MF_CAPTURE);
            }
        }
        // Fous
        bbp=p.bb[us][BISHOP];
        while(bbp){
            int s=pop_lsb(bbp);
            U64 t = bishop_attacks(s,occ) & opp;
            while(t){
                int to=pop_lsb(t);
                moves[n++]=make_move_int(s,to,0,MF_CAPTURE);
            }
        }
        // Tours
        bbp=p.bb[us][ROOK];
        while(bbp){
            int s=pop_lsb(bbp);
            U64 t = rook_attacks(s,occ) & opp;
            while(t){
                int to=pop_lsb(t);
                moves[n++]=make_move_int(s,to,0,MF_CAPTURE);
            }
        }
        // Dames
        bbp=p.bb[us][QUEEN];
        while(bbp){
            int s=pop_lsb(bbp);
            U64 t = queen_attacks(s,occ) & opp;
            while(t){
                int to=pop_lsb(t);
                moves[n++]=make_move_int(s,to,0,MF_CAPTURE);
            }
        }
        // Roi (captures seulement, pas de roques)
        bbp=p.bb[us][KING];
        if(bbp){
            int s=pop_lsb(bbp);
            U64 t = king_att[s] & opp;
            while(t){
                int to=pop_lsb(t);
                moves[n++]=make_move_int(s,to,0,MF_CAPTURE);
            }
        }
        return n;
    }

    // Cavaliers (tous coups)
    {
        U64 bbp=p.bb[us][KNIGHT];
        while(bbp){
            int s=pop_lsb(bbp);
            U64 t=knight_att[s] & ~own;
            while(t){
                int to=pop_lsb(t);
                int flags=(opp&bb_one(to))?MF_CAPTURE:0;
                moves[n++]=make_move_int(s,to,0,flags);
            }
        }
    }
    // Fous
    {
        U64 bbp=p.bb[us][BISHOP];
        while(bbp){
            int s=pop_lsb(bbp);
            U64 t=bishop_attacks(s,occ) & ~own;
            while(t){
                int to=pop_lsb(t);
                int flags=(opp&bb_one(to))?MF_CAPTURE:0;
                moves[n++]=make_move_int(s,to,0,flags);
            }
        }
    }
    // Tours
    {
        U64 bbp=p.bb[us][ROOK];
        while(bbp){
            int s=pop_lsb(bbp);
            U64 t=rook_attacks(s,occ) & ~own;
            while(t){
                int to=pop_lsb(t);
                int flags=(opp&bb_one(to))?MF_CAPTURE:0;
                moves[n++]=make_move_int(s,to,0,flags);
            }
        }
    }
    // Dames
    {
        U64 bbp=p.bb[us][QUEEN];
        while(bbp){
            int s=pop_lsb(bbp);
            U64 t=queen_attacks(s,occ) & ~own;
            while(t){
                int to=pop_lsb(t);
                int flags=(opp&bb_one(to))?MF_CAPTURE:0;
                moves[n++]=make_move_int(s,to,0,flags);
            }
        }
    }

    // Roi + roques
    {
        U64 bbp=p.bb[us][KING];
        if(bbp){
            int s=pop_lsb(bbp);
            U64 t=king_att[s] & ~own;
            while(t){
                int to=pop_lsb(t);
                int flags=(opp&bb_one(to))?MF_CAPTURE:0;
                moves[n++]=make_move_int(s,to,0,flags);
            }
            Color themC = them;
            if(us==WHITE){
                if(p.castling&1){
                    if(!p.board[sq(5,0)] && !p.board[sq(6,0)] &&
                       !square_attacked(p,s,themC) &&
                       !square_attacked(p,sq(5,0),themC) &&
                       !square_attacked(p,sq(6,0),themC))
                        moves[n++]=make_move_int(s,sq(6,0),0,MF_KSCASTLE);
                }
                if(p.castling&2){
                    if(!p.board[sq(1,0)] && !p.board[sq(2,0)] && !p.board[sq(3,0)] &&
                       !square_attacked(p,s,themC) &&
                       !square_attacked(p,sq(2,0),themC) &&
                       !square_attacked(p,sq(3,0),themC))
                        moves[n++]=make_move_int(s,sq(2,0),0,MF_QSCASTLE);
                }
            }else{
                if(p.castling&4){
                    if(!p.board[sq(5,7)] && !p.board[sq(6,7)] &&
                       !square_attacked(p,s,themC) &&
                       !square_attacked(p,sq(5,7),themC) &&
                       !square_attacked(p,sq(6,7),themC))
                        moves[n++]=make_move_int(s,sq(6,7),0,MF_KSCASTLE);
                }
                if(p.castling&8){
                    if(!p.board[sq(1,7)] && !p.board[sq(2,7)] && !p.board[sq(3,7)] &&
                       !square_attacked(p,s,themC) &&
                       !square_attacked(p,sq(2,7),themC) &&
                       !square_attacked(p,sq(3,7),themC))
                        moves[n++]=make_move_int(s,sq(2,7),0,MF_QSCASTLE);
                }
            }
        }
    }
    return n;
}

// --- make / unmake ---

inline void make_move(Position &p,int m,Undo &u){
    u.prev = p; // snapshot avant modifs

    int from=move_from(m), to=move_to(m);
    Piece pc=p.board[from];
    Piece captured=p.board[to];

    // retirer EP hash
    if(p.ep != -1){
        p.key ^= zob_ep[file_of(p.ep)];
    }
    p.ep = -1;

    int oldCastling = p.castling;

    // EP
    if(m & MF_ENPASSANT){
        int cap_sq = to + (p.stm==WHITE ? -8 : 8);
        captured = p.board[cap_sq];
        remove_piece(p, cap_sq);
    }

    // droits de roque (roi)
    if(piece_type(pc)==KING){
        if(p.stm==WHITE) p.castling &= ~3;
        else             p.castling &= ~12;
    }

    // droits de roque (tours qui bougent)
    if(piece_type(pc)==ROOK){
        if(from==sq(0,0))p.castling&=~2;
        if(from==sq(7,0))p.castling&=~1;
        if(from==sq(0,7))p.castling&=~8;
        if(from==sq(7,7))p.castling&=~4;
    }
    // droits de roque (tours capturées)
    if(captured==W_ROOK){
        if(to==sq(0,0))p.castling&=~2;
        if(to==sq(7,0))p.castling&=~1;
    }else if(captured==B_ROOK){
        if(to==sq(0,7))p.castling&=~8;
        if(to==sq(7,7))p.castling&=~4;
    }

    // MAJ zobrist castling
    if(oldCastling != p.castling){
        p.key ^= zob_castle[oldCastling & 15];
        p.key ^= zob_castle[p.castling & 15];
    }

    // captures normales
    if(!(m & MF_ENPASSANT) && captured!=EMPTY){
        remove_piece(p, to);
    }

    // promotion ou déplacement
    if(m & MF_PROMO){
        remove_piece(p, from);
        PieceType pt=(PieceType)move_promo(m);
        Piece new_pc=make_piece(p.stm,pt);
        add_piece(p, to, new_pc);
    }else{
        move_piece(p, from, to);
    }

    // roque : déplacement tour
    if(piece_type(pc)==KING){
        if(m & MF_KSCASTLE){
            if(p.stm==WHITE){
                move_piece(p, sq(7,0), sq(5,0));
            }else{
                move_piece(p, sq(7,7), sq(5,7));
            }
        }else if(m & MF_QSCASTLE){
            if(p.stm==WHITE){
                move_piece(p, sq(0,0), sq(3,0));
            }else{
                move_piece(p, sq(0,7), sq(3,7));
            }
        }
    }

    // double push -> EP
    if(piece_type(pc)==PAWN){
        int from_r=rank_of(from), to_r=rank_of(to);
        if((p.stm==WHITE && from_r==1 && to_r==3) ||
           (p.stm==BLACK && from_r==6 && to_r==4)){
            p.ep = (from+to)/2;
            p.key ^= zob_ep[file_of(p.ep)];
        }
    }

    // clocks
    if(piece_type(pc)==PAWN || captured!=EMPTY) p.halfmove=0;
    else p.halfmove++;
    if(p.stm==BLACK) p.fullmove++;

    // side to move
    p.stm = (Color)(p.stm^1);
    p.key ^= zob_side;
}

inline void unmake_move(Position &p,const Undo &u){
    p = u.prev;
}

// --- Interface partie (historique global) ---

inline void start_new_game(Position &p){
    set_startpos(p);
    game_ply = 1;
    game_history[0] = p.key;
}

// À appeler par la GUI quand un coup est joué (par toi ou par l’engine)
inline void apply_game_move(Position &p, int m){
    Undo u;
    make_move(p, m, u); // met à jour p.key
    if(game_ply < 4096){
        game_history[game_ply++] = p.key;
    }
}

// --- PST & évaluation ---

// PST MG
static const int PST_MG[6][64] = {
// PAWN
{
  0,  0,  0,  0,  0,  0,  0,  0,
 50, 50, 50, 50, 50, 50, 50, 50,
 10, 10, 20, 30, 30, 20, 10, 10,
  5,  5, 10, 27, 27, 10,  5,  5,
  0,  0,  0, 25, 25,  0,  0,  0,
  5, -5,-10,  0,  0,-10, -5,  5,
  5, 10, 10,-25,-25, 10, 10,  5,
  0,  0,  0,  0,  0,  0,  0,  0
},
// KNIGHT
{
-50,-40,-30,-30,-30,-30,-40,-50,
-40,-20,  0,  5,  5,  0,-20,-40,
-30,  5, 10, 15, 15, 10,  5,-30,
-30,  0, 15, 20, 20, 15,  0,-30,
-30,  5, 15, 20, 20, 15,  5,-30,
-30,  0, 10, 15, 15, 10,  0,-30,
-40,-20,  0,  0,  0,  0,-20,-40,
-50,-40,-30,-30,-30,-30,-40,-50
},
// BISHOP
{
-20,-10,-10,-10,-10,-10,-10,-20,
-10,  5,  0,  0,  0,  0,  5,-10,
-10, 10, 10, 10, 10, 10, 10,-10,
-10,  0, 10, 10, 10, 10,  0,-10,
-10,  5,  5, 10, 10,  5,  5,-10,
-10,  0,  5, 10, 10,  5,  0,-10,
-10,  0,  0,  0,  0,  0,  0,-10,
-20,-10,-10,-10,-10,-10,-10,-20
},
// ROOK
{
  0,  0,  5, 10, 10,  5,  0,  0,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
  5, 10, 10, 10, 10, 10, 10,  5,
  0,  0,  0,  0,  0,  0,  0,  0
},
// QUEEN
{
-20,-10,-10, -5, -5,-10,-10,-20,
-10,  0,  5,  0,  0,  0,  0,-10,
-10,  5,  5,  5,  5,  5,  0,-10,
 -5,  0,  5,  5,  5,  5,  0, -5,
  0,  0,  5,  5,  5,  5,  0, -5,
-10,  0,  5,  5,  5,  5,  0,-10,
-10,  0,  0,  0,  0,  0,  0,-10,
-20,-10,-10, -5, -5,-10,-10,-20
},
// KING MG
{
-30,-40,-40,-50,-50,-40,-40,-30,
-30,-40,-40,-50,-50,-40,-40,-30,
-30,-40,-40,-50,-50,-40,-40,-30,
-30,-40,-40,-50,-50,-40,-40,-30,
-20,-30,-30,-40,-40,-30,-30,-20,
-10,-20,-20,-20,-20,-20,-20,-10,
 20, 20,  0,  0,  0,  0, 20, 20,
 20, 30, 10,  0,  0, 10, 30, 20
}
};

// PST EG
static const int PST_EG[6][64] = {
// PAWN
{
  0,  0,  0,  0,  0,  0,  0,  0,
 10, 10, 10, 10, 10, 10, 10, 10,
  0,  0,  5, 10, 10,  5,  0,  0,
  0,  0, 10, 20, 20, 10,  0,  0,
  0,  0, 10, 25, 25, 10,  0,  0,
  0,  0,  5, 10, 10,  5,  0,  0,
  0,  0,  0,-10,-10,  0,  0,  0,
  0,  0,  0,  0,  0,  0,  0,  0
},
// KNIGHT
{
-40,-30,-20,-20,-20,-20,-30,-40,
-30,-10,  0,  0,  0,  0,-10,-30,
-20,  0, 10, 15, 15, 10,  0,-20,
-20,  5, 15, 20, 20, 15,  5,-20,
-20,  0, 15, 20, 20, 15,  0,-20,
-20,  5, 10, 15, 15, 10,  5,-20,
-30,-10,  0,  0,  0,  0,-10,-30,
-40,-30,-20,-20,-20,-20,-30,-40
},
// BISHOP
{
-20,-10,-10,-10,-10,-10,-10,-20,
-10,  0,  0,  0,  0,  0,  0,-10,
-10,  0,  5, 10, 10,  5,  0,-10,
-10,  5, 10, 15, 15, 10,  5,-10,
-10,  0, 10, 15, 15, 10,  0,-10,
-10,  5,  5, 10, 10,  5,  5,-10,
-10,  0,  0,  0,  0,  0,  0,-10,
-20,-10,-10,-10,-10,-10,-10,-20
},
// ROOK
{
  0,  0,  5, 15, 15,  5,  0,  0,
 -5,  0,  0,  5,  5,  0,  0, -5,
 -5,  0,  0,  5,  5,  0,  0, -5,
 -5,  0,  0,  5,  5,  0,  0, -5,
 -5,  0,  0,  5,  5,  0,  0, -5,
 -5,  0,  0,  5,  5,  0,  0, -5,
  5, 10, 10, 15, 15, 10, 10,  5,
  0,  0,  0,  5,  5,  0,  0,  0
},
// QUEEN
{
-10,-10,-10, -5, -5,-10,-10,-10,
-10,  0,  0,  0,  0,  0,  0,-10,
-10,  0,  5,  5,  5,  5,  0,-10,
 -5,  0,  5,  5,  5,  5,  0, -5,
  0,  0,  5,  5,  5,  5,  0, -5,
-10,  0,  5,  5,  5,  5,  0,-10,
-10,  0,  0,  0,  0,  0,  0,-10,
-10,-10,-10, -5, -5,-10,-10,-10
},
// KING EG
{
-50,-40,-30,-20,-20,-30,-40,-50,
-30,-20,-10,  0,  0,-10,-20,-30,
-30,-10, 20, 30, 30, 20,-10,-30,
-30,-10, 30, 40, 40, 30,-10,-30,
-30,-10, 30, 40, 40, 30,-10,-30,
-30,-10, 20, 30, 30, 20,-10,-30,
-30,-30,  0,  0,  0,  0,-30,-30,
-50,-40,-30,-20,-20,-30,-40,-50
}
};

// petits helpers éval
inline int is_center_sq(int s){
    int f=file_of(s), r=rank_of(s);
    return ( (f==3||f==4) && (r==3||r==4) );
}
inline bool is_knight_start(Color c,int s){
    return (c==WHITE && (s==sq(1,0)||s==sq(6,0))) ||
           (c==BLACK && (s==sq(1,7)||s==sq(6,7)));
}
inline bool is_bishop_start(Color c,int s){
    return (c==WHITE && (s==sq(2,0)||s==sq(5,0))) ||
           (c==BLACK && (s==sq(2,7)||s==sq(5,7)));
}
inline bool is_king_castled(Color c,int s){
    return (c==WHITE && (s==sq(6,0)||s==sq(2,0))) ||
           (c==BLACK && (s==sq(6,7)||s==sq(2,7)));
}

// éval d'un camp
inline int eval_side(const Position &p, Color c, int phase, const int pawnFileCount[2][8]){
    int mg=0,eg=0;
    U64 own_occ = p.occ[c];
    U64 all_occ = p.occ_all;

    const int *myPawns  = pawnFileCount[c];
    const int *oppPawns = pawnFileCount[c^1];

    for(int s=0;s<64;s++){
        Piece pc = p.board[s];
        if(pc==EMPTY) continue;
        if(piece_color(pc)!=c) continue;
        PieceType t = (PieceType)piece_type(pc);
        int idx = (c==WHITE ? s : 63-s);

        int v = VAL[t];
        mg += v + PST_MG[t][idx];
        eg += v + PST_EG[t][idx];

        // centre
        if(is_center_sq(s)){
            if(t==PAWN) { mg += 10; eg += 5; }
            else if(t==KNIGHT || t==BISHOP){ mg += 8; eg += 5; }
            else if(t==QUEEN){ mg += 4; }
        }

        // développement
        if(phase > 12){
            if(t==KNIGHT && is_knight_start(c,s)) mg -= 10;
            if(t==BISHOP && is_bishop_start(c,s)) mg -= 10;
        }

        // pions
        if(t==PAWN){
            int f = file_of(s);
            int rRank = rank_of(s);
            int r = (c==WHITE ? rRank : 7-rRank);

            bool doubled  = myPawns[f] > 1;
            bool isolated = ((f==0 || myPawns[f-1]==0) &&
                             (f==7 || myPawns[f+1]==0));
            if(doubled){  mg -= 10; eg -= 5; }
            if(isolated){ mg -= 15; eg -=10; }

            // pion arriéré (simple)
            bool backward = false;
            if(!isolated){
                bool frontEnemy = false;
                if(c==WHITE){
                    for(int rr=rRank+1; rr<8; ++rr){
                        Piece pc2 = p.board[sq(f,rr)];
                        if(pc2!=EMPTY && piece_color(pc2)==(c^1) && piece_type(pc2)==PAWN){
                            frontEnemy = true; break;
                        }
                    }
                }else{
                    for(int rr=rRank-1; rr>=0; --rr){
                        Piece pc2 = p.board[sq(f,rr)];
                        if(pc2!=EMPTY && piece_color(pc2)==(c^1) && piece_type(pc2)==PAWN){
                            frontEnemy = true; break;
                        }
                    }
                }
                bool hasSupport = false;
                if(c==WHITE){
                    for(int df=-1; df<=1; df+=2){
                        int ff=f+df; if(ff<0||ff>7)continue;
                        for(int rr=0; rr<=rRank; ++rr){
                            Piece pc2=p.board[sq(ff,rr)];
                            if(pc2!=EMPTY && piece_color(pc2)==c && piece_type(pc2)==PAWN){
                                hasSupport=true; break;
                            }
                        }
                    }
                }else{
                    for(int df=-1; df<=1; df+=2){
                        int ff=f+df; if(ff<0||ff>7)continue;
                        for(int rr=7; rr>=rRank; --rr){
                            Piece pc2=p.board[sq(ff,rr)];
                            if(pc2!=EMPTY && piece_color(pc2)==c && piece_type(pc2)==PAWN){
                                hasSupport=true; break;
                            }
                        }
                    }
                }
                backward = frontEnemy && !hasSupport;
            }
            if(backward){ mg -= 10; eg -= 10; }

            // pion passé
            bool blocked=false;
            for(int rr=rRank+(c==WHITE?1:-1);
                (c==WHITE? rr<8:rr>=0);
                rr+=(c==WHITE?1:-1)){
                int sqf = sq(f,rr);
                Piece pc2=p.board[sqf];
                if(pc2!=EMPTY && piece_color(pc2)==(c^1) && piece_type(pc2)==PAWN){
                    blocked=true;break;
                }
            }
            if(!blocked){
                int bonus = r*10;
                mg += bonus;
                eg += bonus*2;

                // protégé par pion
                bool protectedByPawn=false;
                int dir=(c==WHITE?1:-1);
                int defRank=rRank-dir;
                if(defRank>=0&&defRank<8){
                    for(int df=-1; df<=1; df+=2){
                        int ff=f+df; if(ff<0||ff>7)continue;
                        Piece pc2=p.board[sq(ff,defRank)];
                        if(pc2!=EMPTY && piece_color(pc2)==c && piece_type(pc2)==PAWN){
                            protectedByPawn=true; break;
                        }
                    }
                }
                if(protectedByPawn){ mg += 15; eg += 25; }

                // pion passé connecté
                bool connected=false;
                for(int df=-1; df<=1; df+=2){
                    int ff=f+df; if(ff<0||ff>7)continue;
                    for(int rr=0; rr<8; ++rr){
                        Piece pc2=p.board[sq(ff,rr)];
                        if(pc2!=EMPTY && piece_color(pc2)==c && piece_type(pc2)==PAWN){
                            connected=true; break;
                        }
                    }
                }
                if(connected){ mg += 10; eg += 15; }
            }
        }

        // mobilité
        if(t==KNIGHT){
            U64 att = knight_att[s] & ~own_occ;
            mg += 2 * bb_count(att);
        }else if(t==BISHOP){
            U64 att = bishop_attacks(s,all_occ) & ~own_occ;
            mg += 2 * bb_count(att);
        }else if(t==ROOK){
            U64 att = rook_attacks(s,all_occ) & ~own_occ;
            int mob = bb_count(att);
            mg += mob;
            int f=file_of(s);
            int my = myPawns[f];
            int op = oppPawns[f];
            if(my==0 && op==0){       // colonne ouverte
                mg += 15; eg += 10;
            }else if(my==0 && op>0){ // semi-ouverte
                mg += 8;  eg += 5;
            }
        }else if(t==QUEEN){
            U64 att = queen_attacks(s,all_occ) & ~own_occ;
            int mob = bb_count(att);
            mg += mob;
            eg += mob;
        }
    }

    // sécurité roi
    U64 kbb = p.bb[c][KING];
    if(kbb){
        int ks = __builtin_ctzll(kbb);
        int r = (c==WHITE? rank_of(ks): 7-rank_of(ks));
        bool castled = is_king_castled(c,ks);
        if(castled) mg += 30;
        else if(phase > 12 && (ks==sq(4,0) || ks==sq(4,7))) mg -= 30;

        // bouclier de pions
        int shield = 0;
        int kf=file_of(ks), kr=rank_of(ks);
        for(int df=-1; df<=1; df++){
            int ff=kf+df;
            int rr=kr + (c==WHITE?1:-1);
            if(ff<0||ff>7||rr<0||rr>7) continue;
            Piece pc = p.board[sq(ff,rr)];
            if(pc!=EMPTY && piece_color(pc)==c && piece_type(pc)==PAWN)
                shield++;
        }
        mg += shield*8;
        if(shield==0 && phase>8) mg -= 20;

        // roi actif en finale
        if(phase<8){
            eg += (3-r)*5;
        }
    }

    if(phase<0) phase=0;
    if(phase>24) phase=24;

    // CORRECTION : plus de matériel = plus de poids pour mg
    int score = (mg*phase + eg*(24-phase)) / 24;
    return score;
}

// éval globale
inline int eval(const Position &p){
    int phase=0;
    for(int c=0;c<2;c++){
        for(int t=KNIGHT;t<=QUEEN;t++){
            int w = (t==QUEEN?4:(t==ROOK?2:1));
            phase += w * bb_count(p.bb[c][t]);
        }
    }
    if(phase>24) phase=24;
    if(phase<0)  phase=0;

    int pawnFileCount[2][8] = {};
    for(int s=0; s<64; ++s){
        Piece pc = p.board[s];
        if(pc==EMPTY) continue;
        if(piece_type(pc)!=PAWN) continue;
        int c = piece_color(pc);
        int f = file_of(s);
        pawnFileCount[c][f]++;
    }

    int white = eval_side(p,WHITE,phase,pawnFileCount);
    int black = eval_side(p,BLACK,phase,pawnFileCount);
    int score = white - black;
    return (p.stm==WHITE ? score : -score);
}

// --- 3 répétitions & 50 coups ---

inline int repetition_count(const Position &p, int ply){
    int start = ply - p.halfmove;
    if(start < 0) start = 0;
    int count = 0;
    for(int i = ply; i >= start; --i){
        if(rep_history[i] == p.key) ++count;
    }
    return count;
}

// --- TT & recherche ---

inline int tt_index(U64 key){
    return (int)((key>>32)&(TT_SIZE-1));
}

inline int probe_tt(U64 key,int depth,int alpha,int beta,int &ttMove){
    TTEntry &e=TT[tt_index(key)];
    if(e.key!=key) return std::numeric_limits<int>::min();
    ttMove=e.move;
    if(e.depth>=depth){
        int s=e.score;
        if(e.flag==0) return s;          // exact
        if(e.flag==1 && s<=alpha) return alpha; // upper
        if(e.flag==2 && s>=beta)  return beta;  // lower
    }
    return std::numeric_limits<int>::min();
}

inline void store_tt(U64 key,int depth,int score,int flag,int move){
    TTEntry &e=TT[tt_index(key)];
    if(depth>=e.depth || e.key==0){
        e.key=key; e.depth=depth; e.score=score; e.flag=flag; e.move=move;
    }
}

static std::chrono::steady_clock::time_point search_end;
static bool stop_search=false;
static int nodes=0;

inline int get_nodes(){ return nodes; }

// null-move
inline bool has_non_pawn_material(const Position &p, Color c){
    return (p.bb[c][KNIGHT] | p.bb[c][BISHOP] | p.bb[c][ROOK] | p.bb[c][QUEEN]) != 0;
}

inline void make_null_move(Position &p, Undo &u){
    u.prev = p;
    if(p.ep != -1){
        p.key ^= zob_ep[file_of(p.ep)];
    }
    p.ep = -1;
    p.stm = (Color)(p.stm ^ 1);
    p.key ^= zob_side;
}

// move ordering
struct ScoredMove{
    int move;
    int score;
};

inline int score_move(const Position &p, int m, int ttMove, int ply){
    int s = 0;
    if(m == ttMove) s += 100000000;

    bool isCap = move_is_capture(m);
    if(isCap){
        int from = move_from(m);
        int to   = move_to(m);
        Piece attacker = p.board[from];
        int attackerT = attacker ? piece_type(attacker) : 6;
        int victimT;
        if(m & MF_ENPASSANT){
            victimT = PAWN;
        }else{
            Piece victim = p.board[to];
            victimT = victim ? piece_type(victim) : 6;
        }
        s += 1000000 + MVV_LVA[victimT][attackerT];
        if(m & MF_PROMO) s += 5000;
    }else{
        if(m & (MF_KSCASTLE|MF_QSCASTLE)){
            s += 20000;
        }else{
            if(ply < MAX_PLY){
                if(m == killer_moves[0][ply])      s += 9000;
                else if(m == killer_moves[1][ply]) s += 8000;
            }
            Color us = p.stm;
            int from = move_from(m), to = move_to(m);
            s += history_heur[us][from][to];
        }
    }
    return s;
}

// quiescence
inline int quiescence(Position &p,int alpha,int beta,int ply){
    if(stop_search) return 0;
    if(std::chrono::steady_clock::now()>=search_end){
        stop_search=true; return 0;
    }
    nodes++;

    rep_history[ply] = p.key;

    if(p.halfmove >= 100 || repetition_count(p, ply) >= 3)
        return 0;

    int stand=eval(p);
    if(stand>=beta) return beta;
    if(stand>alpha) alpha=stand;

    int moves[256];
    int n=generate_moves(p,moves,true);
    for(int i=0;i<n;i++){
        int m=moves[i];
        Undo u; make_move(p,m,u);
        if(in_check(p,(Color)(p.stm^1))){
            unmake_move(p,u); continue;
        }
        rep_history[ply+1] = p.key;
        int score=-quiescence(p,-beta,-alpha,ply+1);
        unmake_move(p,u);
        if(stop_search) return 0;
        if(score>=beta) return beta;
        if(score>alpha) alpha=score;
    }
    return alpha;
}

// alpha-beta
inline int search(Position &p,int depth,int alpha,int beta,int ply){
    if(stop_search) return 0;
    if(std::chrono::steady_clock::now()>=search_end){
        stop_search=true; return 0;
    }
    nodes++;

    rep_history[ply] = p.key;

    if(p.halfmove >= 100 || repetition_count(p, ply) >= 3)
        return 0;

    if(depth<=0)
        return quiescence(p,alpha,beta,ply);

    Color us = p.stm;
    bool inCheckHere = in_check(p, us);
    int alphaOrig = alpha;

    int ttMove=0;
    int ttScore=probe_tt(p.key,depth,alpha,beta,ttMove);
    if(ttScore!=std::numeric_limits<int>::min())
        return ttScore;

    int staticEval = 0;
    bool useFutility = false;
    if(depth==1 && !inCheckHere){
        staticEval = eval(p);
        useFutility = true;
        if(staticEval >= beta)
            return staticEval;
    }

    // null move
    if(depth >= 3 && !inCheckHere && has_non_pawn_material(p, us) && ply < MAX_PLY-1){
        Undo u;
        make_null_move(p, u);
        rep_history[ply+1] = p.key;
        int R = 2 + (depth > 5 ? 1 : 0);
        int score = -search(p, depth-1-R, -beta, -beta+1, ply+1);
        unmake_move(p, u);
        if(stop_search) return 0;
        if(score >= beta) return beta;
    }

    int moves[256];
    int n=generate_moves(p,moves,false);
    ScoredMove sm[256];
    for(int i=0;i<n;i++){
        sm[i].move  = moves[i];
        sm[i].score = score_move(p, moves[i], ttMove, ply);
    }
    std::sort(sm, sm+n, [](const ScoredMove &a,const ScoredMove &b){
        return a.score > b.score;
    });

    int bestScore=-INF;
    int bestMove=0;
    bool any=false;

    for(int i=0;i<n;i++){
        int m = sm[i].move;
        Undo u; make_move(p,m,u);
        if(in_check(p,(Color)(p.stm^1))){
            unmake_move(p,u); continue;
        }
        any=true;

        // futility (depth==1, quiet)
        if(useFutility &&
           !move_is_capture(m) &&
           !(m & (MF_PROMO|MF_ENPASSANT|MF_KSCASTLE|MF_QSCASTLE)) &&
           staticEval + FUTILITY_MARGIN <= alpha){
            unmake_move(p,u);
            continue;
        }

        rep_history[ply+1] = p.key;

        int score;
        bool isCapture = move_is_capture(m) || (m & MF_PROMO);

        // LMR
        if(!isCapture && !inCheckHere && depth >= 3 && i > 3 && ply > 0){
            int R = 1 + (depth > 5 && i > 7 ? 1 : 0);
            int reducedDepth = depth-1-R;
            score = -search(p, reducedDepth, -beta, -alpha, ply+1);
            if(score > alpha){
                score = -search(p, depth-1, -beta, -alpha, ply+1);
            }
        }else{
            score = -search(p,depth-1,-beta,-alpha,ply+1);
        }

        unmake_move(p,u);
        if(stop_search) return 0;

        if(score>bestScore){
            bestScore=score;
            bestMove=m;
        }
        if(score>alpha){
            alpha=score;
            if(alpha>=beta){
                if(!move_is_capture(m) && !(m & (MF_KSCASTLE|MF_QSCASTLE)) && ply < MAX_PLY){
                    if(killer_moves[0][ply] != m){
                        killer_moves[1][ply] = killer_moves[0][ply];
                        killer_moves[0][ply] = m;
                    }
                    int from = move_from(m), to = move_to(m);
                    history_heur[us][from][to] += depth*depth;
                }
                break;
            }
        }
    }

    if(!any){
        if(in_check(p,p.stm)) return -MATE+ply;
        return 0; // pat
    }

    int flag;
    if(bestScore <= alphaOrig)      flag = 1; // upper
    else if(bestScore >= beta)      flag = 2; // lower
    else                            flag = 0; // exact

    store_tt(p.key,depth,bestScore,flag,bestMove);
    return bestScore;
}

// iterative deepening
inline int search_best_move(Position &p,int time_ms,int max_depth,int &out_move){
    nodes=0;
    stop_search=false;
    search_end=std::chrono::steady_clock::now()+std::chrono::milliseconds(time_ms);

    // reset heuristiques
    for(int ply=0; ply<MAX_PLY; ++ply){
        killer_moves[0][ply] = killer_moves[1][ply] = 0;
    }
    for(int c=0;c<2;c++)
        for(int f=0;f<64;f++)
            for(int t=0;t<64;t++)
                history_heur[c][f][t] = 0;

    // si aucune histoire, on initialise avec la position courante
    if(game_ply == 0){
        game_ply = 1;
        game_history[0] = p.key;
    }

    int maxHist = std::min(game_ply, 4096);
    for(int i=0;i<maxHist;i++){
        rep_history[i] = game_history[i];
    }
    int base_ply = maxHist - 1;
    if(base_ply < 0) base_ply = 0;

    int best=0;
    int bestScore=-INF;

    for(int d=1; d<=max_depth; d++){
        if(stop_search) break;

        int moves[256];
        int n=generate_moves(p,moves,false);
        ScoredMove sm[256];

        int ttRootMove=0;
        (void)probe_tt(p.key,d,-INF,INF,ttRootMove);

        for(int i=0;i<n;i++){
            sm[i].move  = moves[i];
            sm[i].score = score_move(p, moves[i], ttRootMove, base_ply);
        }
        std::sort(sm, sm+n, [](const ScoredMove &a,const ScoredMove &b){
            return a.score > b.score;
        });

        int localBest=0;
        int localScore=-INF;

        for(int i=0;i<n;i++){
            int m=sm[i].move;
            Undo u; make_move(p,m,u);
            if(in_check(p,(Color)(p.stm^1))){
                unmake_move(p,u); continue;
            }
            int child_ply = base_ply + 1;
            if(child_ply < 4096){
                rep_history[child_ply] = p.key;
            }
            int score = -search(p,d-1,-INF,INF,child_ply);
            unmake_move(p,u);
            if(stop_search) break;
            if(score>localScore){
                localScore=score;
                localBest=m;
            }
        }
        if(stop_search) break;
        if(localBest){
            best=localBest;
            bestScore=localScore;
        }
    }
    out_move=best;
    return bestScore;
}

// --- Helper pour afficher un coup "e2e4", "e7e8q", etc. ---
inline std::string move_to_str(int m){
    int f = move_from(m);
    int t = move_to(m);
    int ff = file_of(f), rf = rank_of(f);
    int ft = file_of(t), rt = rank_of(t);

    std::string s;
    s += char('a' + ff); s += char('1' + rf);
    s += char('a' + ft); s += char('1' + rt);

    if(move_is_promo(m)){
        int pt = move_promo(m);
        char c = 'q';
        if(pt == KNIGHT)      c = 'n';
        else if(pt == BISHOP) c = 'b';
        else if(pt == ROOK)   c = 'r';
        s += c;
    }
    return s;
}

} // namespace cechess
