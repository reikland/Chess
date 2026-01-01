#include <iostream>
#include <string>
#include <sstream>
#include <cctype>
#include <vector>
#include <limits>
#include "engine2.hpp"

using namespace cechess;

// =========================
// Affichage du plateau (joli)
// =========================

void print_board(const Position &p) {
    auto piece_to_utf8 = [&](Piece pc) -> std::string {
        switch (pc) {
            case W_PAWN:   return "♙";
            case W_KNIGHT: return "♘";
            case W_BISHOP: return "♗";
            case W_ROOK:   return "♖";
            case W_QUEEN:  return "♕";
            case W_KING:   return "♔";
            case B_PAWN:   return "♟";
            case B_KNIGHT: return "♞";
            case B_BISHOP: return "♝";
            case B_ROOK:   return "♜";
            case B_QUEEN:  return "♛";
            case B_KING:   return "♚";
            default:       return " ";
        }
    };

    std::cout << "\n  +------------------------+\n";
    for (int r = 7; r >= 0; --r) {
        std::cout << (r + 1) << " |";
        for (int f = 0; f < 8; ++f) {
            int s = sq(f, r);
            Piece pc = p.board[s];
            std::string symbol = piece_to_utf8(pc);

            // a1 sombre => (r+f) pair
            bool dark = ((r + f) & 1) == 0;
            std::string bg = dark ? "\033[48;5;240m" : "\033[48;5;250m";
            std::string fg;
            if (pc == EMPTY) {
                fg = "\033[38;5;240m";
            } else if (pc >= W_PAWN && pc <= W_KING) {
                fg = "\033[38;5;231m";
            } else {
                fg = "\033[38;5;0m";
            }

            std::cout << bg << fg << " " << symbol << " " << "\033[0m";
        }
        std::cout << "|\n";
    }
    std::cout << "  +------------------------+\n";
    std::cout << "    a  b  c  d  e  f  g  h\n";

    std::cout << (p.stm == WHITE ? "Side to move: White\n" : "Side to move: Black\n");
}

// =========================
// Helpers légalité (coup légal vs pseudo-coup)
// =========================

static bool is_legal_move(Position &pos, int m) {
    Undo u;
    make_move(pos, m, u);
    Color justPlayed = (Color)(pos.stm ^ 1);
    bool ok = !in_check(pos, justPlayed);
    unmake_move(pos, u);
    return ok;
}

static int generate_legal_moves(Position &pos, int *out_moves) {
    int pseudo[256];
    int n = generate_moves(pos, pseudo, false);
    int k = 0;
    for (int i = 0; i < n; ++i) {
        if (is_legal_move(pos, pseudo[i])) out_moves[k++] = pseudo[i];
    }
    return k;
}

// =========================
// Nulle 3 répétitions (sur historique réel game_history)
// =========================

static int repetition_count_game(const Position &p) {
    int ply = game_ply - 1;
    if (ply < 0) return 0;

    int start = ply - p.halfmove;
    if (start < 0) start = 0;

    int count = 0;
    for (int i = ply; i >= start; --i) {
        if (game_history[i] == p.key) ++count;
    }
    return count;
}

// =========================
// Utils string
// =========================

static void trim(std::string &s) {
    auto issp = [](unsigned char c){ return std::isspace(c) != 0; };
    size_t b = 0;
    while (b < s.size() && issp((unsigned char)s[b])) ++b;
    size_t e = s.size();
    while (e > b && issp((unsigned char)s[e-1])) --e;
    s = s.substr(b, e - b);
}

static std::string tolower_str(std::string s){
    for(char &c : s) c = (char)std::tolower((unsigned char)c);
    return s;
}

// =========================
// Parsing "e2e4" / "e7e8q"
// =========================

static int parse_coord_move(Position &p, const std::string &input) {
    if (input.size() < 4) return 0;

    std::string s = tolower_str(input);

    int ff = s[0] - 'a';
    int rf = s[1] - '1';
    int ft = s[2] - 'a';
    int rt = s[3] - '1';

    if (ff < 0 || ff > 7 || ft < 0 || ft > 7 ||
        rf < 0 || rf > 7 || rt < 0 || rt > 7) return 0;

    int from = sq(ff, rf), to = sq(ft, rt);

    int wantPromo = 0;
    if (s.size() >= 5) {
        char pc = s[4];
        if      (pc == 'q') wantPromo = QUEEN;
        else if (pc == 'r') wantPromo = ROOK;
        else if (pc == 'b') wantPromo = BISHOP;
        else if (pc == 'n') wantPromo = KNIGHT;
    }

    int moves[256];
    int n = generate_moves(p, moves, false); // pseudo-coups
    for (int i = 0; i < n; i++) {
        int m = moves[i];
        if (move_from(m) == from && move_to(m) == to) {
            if (move_is_promo(m)) {
                if (wantPromo && move_promo(m) == wantPromo)
                    return m;
            } else {
                if (!wantPromo) return m;
            }
        }
    }
    return 0;
}

// =========================
// Promotion interactive (si l'utilisateur tape sans suffixe)
// =========================

static bool is_pawn_promotion_attempt(const Position &p, int from, int to){
    Piece pc = p.board[from];
    if(pc == EMPTY) return false;
    if(piece_color(pc) != p.stm) return false;
    if(piece_type(pc) != PAWN) return false;

    int toRank = rank_of(to);
    if(p.stm == WHITE) return toRank == 7;
    else               return toRank == 0;
}

static char ask_promo_piece(){
    while(true){
        std::cout << "Promotion piece? Enter q/r/b/n (default q): ";
        std::string s;
        if(!std::getline(std::cin, s)) return 'q';
        trim(s);
        s = tolower_str(s);
        if(s.empty()) return 'q';
        char c = s[0];
        if(c=='q' || c=='r' || c=='b' || c=='n') return c;
        std::cout << "Invalid. Please type q, r, b, or n.\n";
    }
}

// =========================
// Config partie
// =========================

enum PlayerKind { HUMAN = 0, ENGINE_PLAYER = 1 };

struct GameConfig {
    PlayerKind white;
    PlayerKind black;
    int engineTimeMs; // temps par défaut
};

static GameConfig setup_game() {
    GameConfig cfg;
    std::cout << "===== C++ Chess Engine =====\n";
    std::cout << "Choose game mode:\n";
    std::cout << "  1) Human (White) vs Engine (Black)\n";
    std::cout << "  2) Engine (White) vs Human (Black)\n";
    std::cout << "  3) Human vs Human\n";
    std::cout << "  4) Engine vs Engine\n";
    std::cout << "Enter choice [1-4]: ";

    int choice = 1;
    if (!(std::cin >> choice)) {
        std::cin.clear();
    }
    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');

    switch (choice) {
        case 2: cfg.white = ENGINE_PLAYER; cfg.black = HUMAN;         break;
        case 3: cfg.white = HUMAN;         cfg.black = HUMAN;         break;
        case 4: cfg.white = ENGINE_PLAYER; cfg.black = ENGINE_PLAYER; break;
        case 1:
        default:
            cfg.white = HUMAN;
            cfg.black = ENGINE_PLAYER;
            break;
    }

    std::cout << "Engine time per move in ms (default 2000): ";
    if (!(std::cin >> cfg.engineTimeMs)) {
        cfg.engineTimeMs = 2000;
        std::cin.clear();
    }
    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
    if (cfg.engineTimeMs <= 0) cfg.engineTimeMs = 2000;

    std::cout << "Configuration:\n";
    std::cout << "  White: " << (cfg.white == HUMAN ? "Human" : "Engine") << "\n";
    std::cout << "  Black: " << (cfg.black == HUMAN ? "Human" : "Engine") << "\n";
    std::cout << "  Engine time: " << cfg.engineTimeMs << " ms\n\n";

    return cfg;
}

static bool is_human_turn(const Position &p, const GameConfig &cfg) {
    if (p.stm == WHITE) return cfg.white == HUMAN;
    return cfg.black == HUMAN;
}

// =========================
// Main loop
// =========================

int main() {
    init_all();

    Position pos;
    start_new_game(pos); // initialise game_history/game_ply

    GameConfig cfg = setup_game();

    std::vector<int> move_history;

    // override one-shot pour le prochain coup engine
    int next_engine_time_ms = -1;

    while (true) {
        print_board(pos);

        // --- fin de partie : aucun coup légal => mat ou pat ---
        int legal_moves[256];
        int nLegal = generate_legal_moves(pos, legal_moves);
        bool checkNow = in_check(pos, pos.stm);

        if (nLegal == 0) {
            if (checkNow) {
                if (pos.stm == WHITE) std::cout << "Échec et mat : les Noirs gagnent.\n";
                else                  std::cout << "Échec et mat : les Blancs gagnent.\n";
            } else {
                std::cout << "Nulle par pat (aucun coup légal).\n";
            }
            break;
        }

        // Échec (uniquement si PAS mat)
        if (checkNow) {
            std::cout << "Échec.\n";
        }

        // --- nulle 50 coups (100 demi-coups) ---
        if (pos.halfmove >= 100) {
            std::cout << "Nulle par règle des 50 coups (halfmove >= 100).\n";
            break;
        }

        // --- nulle 3 répétitions ---
        if (repetition_count_game(pos) >= 3) {
            std::cout << "Nulle par répétition de la position (3 fois).\n";
            break;
        }

        bool humanTurn = is_human_turn(pos, cfg);

        // =========================
        // Tour de l'engine
        // =========================
        if (!humanTurn) {
            int time_ms = (next_engine_time_ms > 0 ? next_engine_time_ms : cfg.engineTimeMs);
            next_engine_time_ms = -1; // one-shot consommé

            std::cout << "[Engine] thinking (" << time_ms << " ms)...\n";

            int bestMove = 0;
            int score = search_best_move(pos, time_ms, 64, bestMove);

            if (!bestMove) {
                bestMove = legal_moves[0]; // fallback
            }

            std::string ms = move_to_str(bestMove);
            apply_game_move(pos, bestMove);
            move_history.push_back(bestMove);

            std::cout << "[Engine] plays: " << ms
                      << " (score " << score
                      << ", nodes " << get_nodes()
                      << ")\n\n";
            continue;
        }

        // =========================
        // Tour humain
        // =========================
        std::cout << "[Human " << (pos.stm == WHITE ? "White" : "Black")
                  << "] enter move (e2e4, 'undo', 'board', 'modify', 'quit'): ";

        std::string line;
        if (!std::getline(std::cin, line)) break;
        trim(line);
        if (line.empty()) continue;

        std::string cmd = tolower_str(line);

        if (cmd == "quit" || cmd == "q") {
            std::cout << "Exiting.\n";
            break;

        } else if (cmd == "board") {
            continue;

        } else if (cmd == "modify" || cmd == "m" || cmd == "time" || cmd == "t") {
            std::cout << "Engine time (ms) for NEXT engine move only (current default "
                      << cfg.engineTimeMs << "). Enter ms (or empty to cancel): ";
            std::string v;
            std::getline(std::cin, v);
            trim(v);
            if (v.empty()) {
                std::cout << "No change.\n";
                continue;
            }
            std::stringstream ss(v);
            int x = 0;
            if (!(ss >> x) || x <= 0) {
                std::cout << "Invalid value. No change.\n";
                continue;
            }
            next_engine_time_ms = x;
            std::cout << "OK. Next engine move will use " << next_engine_time_ms << " ms.\n";
            continue;

        } else if (cmd == "undo" || cmd == "u") {
            if (move_history.empty()) {
                std::cout << "Nothing to undo.\n";
                continue;
            }

            move_history.pop_back();

            start_new_game(pos);     // reset pos + game_history/game_ply
            for (int m : move_history) {
                apply_game_move(pos, m);
            }

            std::cout << "Move undone. Back to previous position.\n";
            continue;

        } else {
            // tentative coup coordonné
            // Si promotion tapée sans suffixe, on demande la pièce.
            if (line.size() == 4) {
                std::string s = tolower_str(line);
                int ff = s[0]-'a', rf = s[1]-'1', ft = s[2]-'a', rt = s[3]-'1';
                if(ff>=0&&ff<8&&ft>=0&&ft<8&&rf>=0&&rf<8&&rt>=0&&rt<8){
                    int from = sq(ff, rf), to = sq(ft, rt);
                    if (is_pawn_promotion_attempt(pos, from, to)) {
                        char pc = ask_promo_piece();
                        line.push_back(pc); // devient ex: "b7a8q"
                    }
                }
            }

            int m = parse_coord_move(pos, line);
            if (!m) {
                std::cout << "Illegal or unknown move. Format example: e2e4 or e7e8q\n";
                continue;
            }

            if (!is_legal_move(pos, m)) {
                std::cout << "Move leaves king in check (illegal).\n";
                continue;
            }

            apply_game_move(pos, m);
            move_history.push_back(m);

            std::cout << "Played: " << line << "\n\n";
        }
    }

    return 0;
}
